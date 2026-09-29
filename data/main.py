import pandas as pd
import random
from datetime import datetime, timedelta

# Load the static Master CSVs generated above
assets = pd.read_csv('assets.csv')
techs = pd.read_csv('technicians.csv')
items = pd.read_csv('inventory_items.csv')

# Configuration for scaling
NUM_WOS_TO_GENERATE = 130  # Adding to the 20 already generated
START_DATE = datetime(2025, 1, 1)

failure_templates = {
    'centrifugal pump': [
        ("Vibration issue on {asset}", "Pump {asset} is shaking badly.", "MECHANICAL", "BEARING_WEAR", "TEAM-MECH"),
        ("Seal leak on {asset}", "Water leaking from {asset} mechanical seal.", "MECHANICAL", "SEAL_FAILURE", "TEAM-MECH"),
        ("Motor hot {asset}", "Motor casing on {asset} very hot.", "ELECTRICAL", "MOTOR_OVERHEATING", "TEAM-ELEC")
    ],
    'conveyor': [
        ("Belt slipping {asset}", "Conveyor {asset} belt slipping under load.", "MECHANICAL", "BELT_MISALIGNMENT", "TEAM-MECH"),
        ("Roller seized {asset}", "Loud scraping noise, roller stuck.", "MECHANICAL", "BEARING_FAILURE", "TEAM-MECH")
    ]
}

new_wos = []
new_history = []

random.seed(42)

for i in range(NUM_WOS_TO_GENERATE):
    asset = assets.sample(1).iloc[0]
    asset_id = asset['asset_id']
    a_type = asset['asset_type']
    
    # Fallback template if asset type not mapped
    templates = failure_templates.get(a_type, [
        ("General issue {asset}", "Operator reported issue with {asset}.", "GENERAL", "UNKNOWN", "TEAM-GEN")
    ])
    
    title_tpl, desc_tpl, expected_class, f_mode, team = random.choice(templates)
    
    wo_id = f"WO-1{i:03d}"
    created_at = START_DATE + timedelta(days=random.randint(1, 300), hours=random.randint(0, 23))
    
    new_wos.append({
        'work_order_id': wo_id,
        'asset_id': asset_id,
        'location_id': asset['location_id'],
        'work_order_type': 'CORRECTIVE',
        'title': title_tpl.format(asset=asset_id),
        'description': desc_tpl.format(asset=asset_id),
        'created_at': created_at.isoformat(),
        'requested_by': 'OPERATOR',
        'assigned_team': team,
        'status': 'COMPLETED',
        'failure_mode': f_mode
    })
    
    # Mirror completed WOs into maintenance history
    new_history.append({
        'maintenance_event_id': f"MH-{i:04d}",
        'asset_id': asset_id,
        'work_order_id': wo_id,
        'event_date': (created_at + timedelta(days=1)).isoformat(),
        'failure_mode': f_mode,
        'failure_cause': 'NORMAL_WEAR',
        'downtime_minutes': random.choice([30, 60, 120])
    })

pd.DataFrame(new_wos).to_csv('work_orders_generated.csv', index=False)
pd.DataFrame(new_history).to_csv('maintenance_history_generated.csv', index=False)
print("Successfully scaled transactional data to required limits.")