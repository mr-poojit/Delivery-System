"""Simulate FastBox package assignments and deliveries."""

import argparse
import csv
import hashlib
import json
import math
import secrets
from pathlib import Path


def load_data(input_path):
    """Read and parse one FastBox JSON input file."""
    with input_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def as_locations(records):
    """Normalize either a list of records or an ID-keyed mapping."""
    if isinstance(records, dict):
        return records

    locations = {}
    for record in records:
        location = record.get("location")
        if location is None:
            raise ValueError(f"Missing location for {record.get('id')}")
        locations[record["id"]] = location
    return locations


def normalize_package(package):
    """Normalize the warehouse key used by both fixture formats."""
    warehouse_id = package.get("warehouse", package.get("warehouse_id"))
    if warehouse_id is None:
        raise ValueError(f"Package {package.get('id')} has no warehouse")
    return {
        "id": package["id"],
        "warehouse": warehouse_id,
        "destination": package["destination"],
    }


def euclidean_distance(first, second):
    """Return the straight-line distance between two [x, y] points."""
    return math.dist(first, second)


def simulate(data, random_delays=False, seed=None, joining_agent=None, return_routes=False):
    """Assign and deliver packages, with optional bonus behavior enabled."""
    warehouses = as_locations(data["warehouses"])
    agents = as_locations(data["agents"])
    packages = [normalize_package(package) for package in data["packages"]]
    routes = {agent_id: [] for agent_id in agents}

    report = {
        agent_id: {
            "packages_delivered": 0,
            "total_distance": 0.0,
            "efficiency": 0.0,
        }
        for agent_id in agents
    }
    if random_delays:
        for agent_summary in report.values():
            agent_summary["total_delay_minutes"] = 0

    midpoint = len(packages) // 2

    for package_index, package in enumerate(packages):
        if joining_agent and package_index == midpoint:
            joining_id = joining_agent["id"]
            if joining_id in agents:
                raise ValueError(f"Joining agent {joining_id} already exists")
            agents[joining_id] = joining_agent["location"]
            routes[joining_id] = []
            report[joining_id] = {
                "packages_delivered": 0,
                "total_distance": 0.0,
                "efficiency": 0.0,
            }
            if random_delays:
                report[joining_id]["total_delay_minutes"] = 0

        warehouse_id = package["warehouse"]
        if warehouse_id not in warehouses:
            raise ValueError(f"Package {package['id']} references unknown warehouse {warehouse_id}")

        assigned_agent = min(
            agents,
            key=lambda agent_id, warehouse_id=warehouse_id: euclidean_distance(
                agents[agent_id], warehouses[warehouse_id]
            ),
        )
        distance = euclidean_distance(agents[assigned_agent], warehouses[warehouse_id])
        distance += euclidean_distance(warehouses[warehouse_id], package["destination"])
        report[assigned_agent]["packages_delivered"] += 1
        report[assigned_agent]["total_distance"] += distance
        routes[assigned_agent].append(
            {
                "package_id": package["id"],
                "warehouse": warehouse_id,
                "destination": package["destination"],
            }
        )
        if random_delays:
            if seed is None:
                delay_minutes = secrets.randbelow(26) + 5
            else:
                seed_text = f"{seed}:{package['id']}".encode("utf-8")
                delay_minutes = int.from_bytes(hashlib.sha256(seed_text).digest()[:4], "big") % 26 + 5
            report[assigned_agent]["total_delay_minutes"] += delay_minutes

    for agent_summary in report.values():
        package_count = agent_summary["packages_delivered"]
        if package_count:
            agent_summary["efficiency"] = (
                agent_summary["total_distance"] / package_count
            )
        agent_summary["total_distance"] = round(agent_summary["total_distance"], 2)
        agent_summary["efficiency"] = round(agent_summary["efficiency"], 2)

    delivered_count = sum(
        agent_summary["packages_delivered"] for agent_summary in report.values()
    )
    if delivered_count != len(packages):
        raise RuntimeError("Not every package was delivered")

    report["best_agent"] = min(
        agents,
        key=lambda agent_id: (
            report[agent_id]["efficiency"]
            if report[agent_id]["packages_delivered"]
            else math.inf,
            list(agents).index(agent_id),
        ),
    )
    if return_routes:
        return report, routes
    return report


def format_ascii_routes(routes):
    """Create a compact text visualization of each agent's assigned routes."""
    lines = ["FastBox Routes", "============="]
    for agent_id, agent_routes in routes.items():
        if not agent_routes:
            lines.append(f"{agent_id}: no packages")
            continue
        stops = [
            f"{route['package_id']}({route['warehouse']} -> {route['destination']})"
            for route in agent_routes
        ]
        lines.append(f"{agent_id}: " + " -> ".join(stops))
    return "\n".join(lines)


def write_top_agent_csv(report, output_path):
    """Export the best agent's summary to a CSV file."""
    best_agent = report["best_agent"]
    summary = report[best_agent]
    columns = ["agent_id", "packages_delivered", "total_distance", "efficiency"]
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=columns)
        writer.writeheader()
        writer.writerow(
            {
                "agent_id": best_agent,
                "packages_delivered": summary["packages_delivered"],
                "total_distance": summary["total_distance"],
                "efficiency": summary["efficiency"],
            }
        )


def main():
    parser = argparse.ArgumentParser(description="Simulate a FastBox delivery day.")
    parser.add_argument("input", type=Path, help="Path to the input JSON file")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("report.json"), help="Output report path"
    )
    parser.add_argument("--random-delays", action="store_true", help="Add random 5-30 minute delays")
    parser.add_argument("--seed", type=int, help="Seed used for reproducible random delays")
    parser.add_argument(
        "--new-agent",
        nargs=3,
        metavar=("ID", "X", "Y"),
        help="Add an agent halfway through the day, for example --new-agent A4 25 25",
    )
    parser.add_argument("--ascii-routes", action="store_true", help="Print assigned routes")
    parser.add_argument("--top-agent-csv", type=Path, help="Export the best agent to CSV")
    args = parser.parse_args()

    joining_agent = None
    if args.new_agent:
        joining_agent = {
            "id": args.new_agent[0],
            "location": [float(args.new_agent[1]), float(args.new_agent[2])],
        }

    report, routes = simulate(
        load_data(args.input),
        random_delays=args.random_delays,
        seed=args.seed,
        joining_agent=joining_agent,
        return_routes=True,
    )
    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    print(json.dumps(report, indent=2))
    if args.ascii_routes:
        print("\n" + format_ascii_routes(routes))
    if args.top_agent_csv:
        write_top_agent_csv(report, args.top_agent_csv)


if __name__ == "__main__":
    main()