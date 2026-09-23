# Delivery System

FastBox is a Python logistics simulator. It assigns packages to the nearest delivery agent, simulates delivery routes, and writes a report containing package counts, total distance, efficiency, and the best agent.

## Requirements

- Python 3.8 or newer
- No third-party packages are required

## Input Format

The simulator accepts both input styles used in this repository:

- `base_case.json` uses lists of warehouse and agent records with `id` and `location` fields.
- Files in `test_cases/` use dictionaries keyed by warehouse or agent ID.

Packages may use either `warehouse` or `warehouse_id` to identify their warehouse.

## Run the Simulator

From the project directory:

```bash
python delivery_system.py base_case.json
```

The command prints the report and writes `report.json` by default. Use `-o` to choose another output file:

```bash
python delivery_system.py test_cases/test_case_1.json -o test_case_1_report.json
```

## Distance and Efficiency

For each package, the simulated route is:

```text
agent -> warehouse -> destination
```

Distances use Euclidean distance:

```text
sqrt((x2 - x1)^2 + (y2 - y1)^2)
```

Efficiency is calculated as:

```text
total_distance / packages_delivered
```

The best agent is the agent with the lowest average distance per delivered package. Agents with no deliveries are not selected when another agent has delivered a package.

## Optional Bonus Features

### Random delivery delays

Add a random delay from 5 to 30 minutes for each package. Use `--seed` when reproducible results are needed:

```bash
python delivery_system.py base_case.json --random-delays --seed 7
```

### ASCII route visualization

```bash
python delivery_system.py base_case.json --ascii-routes
```

### Agent joining during the day

Add an agent halfway through the package list. The arguments are agent ID, X coordinate, and Y coordinate:

```bash
python delivery_system.py base_case.json --new-agent A4 25 25
```

### Export the top agent to CSV

```bash
python delivery_system.py base_case.json --top-agent-csv top_agent.csv
```

All bonus options can be combined:

```bash
python delivery_system.py base_case.json \
  -o bonus_report.json \
  --random-delays --seed 7 \
  --new-agent A4 25 25 \
  --ascii-routes \
  --top-agent-csv top_agent.csv
```

## Test All Fixtures

Run this command from the project directory:

```bash
python -c "from pathlib import Path; from delivery_system import load_data, simulate; paths=[Path('base_case.json'), *sorted(Path('test_cases').glob('test_case_*.json'), key=lambda p: int(p.stem.split('_')[-1]))]; results=[(path, load_data(path), simulate(load_data(path))) for path in paths]; assert all(sum(summary['packages_delivered'] for agent_id, summary in report.items() if agent_id != 'best_agent') == len(data['packages']) for path, data, report in results); print(f'PASS: {len(results)}/{len(results)} fixtures')"
```

The validation covers the base case and all ten numbered test cases. Each report also checks that the total number of delivered packages matches the input package count.

## Files to Commit

Commit the source code, input fixtures, README, and the standard report:

- `delivery_system.py`
- `README.md`
- `base_case.json`
- `test_cases/`
- `report.json`

Bonus output files such as `bonus_report.json` and `top_agent.csv` may also be committed as examples. Do not commit `__pycache__/` or temporary console output such as `bonus_run.txt`.
