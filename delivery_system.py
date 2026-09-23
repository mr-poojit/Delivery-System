"""Simulate FastBox package assignments and deliveries."""

import argparse
import json
import math
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


def simulate(data):
    """Assign and deliver all packages, returning the JSON report shape."""
    warehouses = as_locations(data["warehouses"])
    agents = as_locations(data["agents"])
    packages = [normalize_package(package) for package in data["packages"]]

    report = {
        agent_id: {
            "packages_delivered": 0,
            "total_distance": 0.0,
            "efficiency": 0.0,
        }
        for agent_id in agents
    }

    for package in packages:
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
    return report


def main():
    parser = argparse.ArgumentParser(description="Simulate a FastBox delivery day.")
    parser.add_argument("input", type=Path, help="Path to the input JSON file")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("report.json"), help="Output report path"
    )
    args = parser.parse_args()

    report = simulate(load_data(args.input))
    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()