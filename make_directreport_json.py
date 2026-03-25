import pandas as pd
import json

# =========================
# MANUAL SUPERVISOR INFO
# =========================

# 1. Pull User Curriculum Status report from SFLMS for each manager/supervisor. 

#  Update each time
SUPERVISOR_NAME = "Mike Matos" 

#  Update each time
SUPERVISOR_EMAIL = "mike.matos@thermofisher.com"  

# =========================
# FILE PATHS
# *****Update each time and use the full path
# =========================
csv_file = r"C:\Users\andrea.macgown\OneDrive - Thermo Fisher Scientific\Desktop\TRAINING SYSTEM\splice\mike_matos\mike_matos.csv"
json_file = r"C:\Users\andrea.macgown\OneDrive - Thermo Fisher Scientific\Desktop\TRAINING SYSTEM\splice\mike_matos\mike_matos.json"

'''
1. In the HTML file, update 
            const DATA_FILE = "./riley_magyar_data.json";

            replace "riley_magyar_data.json" with other file title'''
'''
Jim Molinari file: 
    The only code I changed was 
      const DATA_FILE = "./jim_molinari.json";

    Original code: 
        const params = new URLSearchParams(window.location.search);
        const DATA_FILE = "./jim_molinari.json";

        const STORAGE_KEY = "training_removal_progress_" + DATA_FILE;
        const EMAIL_TO = "andrea.macgown@thermofisher.com";

    New code:
            const params = new URLSearchParams(window.location.search);
            const DATA_FILE = "./jim_molinari.json";

            const STORAGE_KEY = "training_removal_progress_" + DATA_FILE;
            const EMAIL_TO = "andrea.macgown@thermofisher.com";
 
    SUCCESS - only change the json file name.
'''

# =========================
# READ CSV
# =========================
df = pd.read_csv(csv_file)

# Fill NaN so string handling is easier
df = df.fillna("")

# =========================
# PASS 1: FIND PARENT CURRICULUM TITLES
# Rule:
# If column 5 == column 6 and Item ID (11) is blank,
# then row[5] is parent curriculum ID and row[7] is parent curriculum title
# =========================
parent_titles = {}

for _, row in df.iterrows():
    col5 = str(row.iloc[5]).strip()
    col6 = str(row.iloc[6]).strip()
    col7 = str(row.iloc[7]).strip()
    item_id = str(row.iloc[11]).strip()

    if col5 and col5 == col6 and not item_id:
        parent_titles[col5] = col7

# =========================
# BUILD TREE + TRAINING LOOKUP
# =========================
tree_map = {}
training_to_reports = {}
employee_training_map = {}
seen_employee_item_pairs = set()

for _, row in df.iterrows():
    employee_id = str(row.iloc[0]).strip()

    first_name = str(row.iloc[2]).strip()
    last_name = str(row.iloc[3]).strip()
    employee_name = f"{first_name} {last_name}".strip()

    parent_curriculum_id = str(row.iloc[5]).strip()
    subcurriculum_id = str(row.iloc[6]).strip()
    subcurriculum_title = str(row.iloc[7]).strip()

    item_id = str(row.iloc[11]).strip()
    item_type = str(row.iloc[12]).strip()
    item_title = str(row.iloc[15]).strip()

    # Rule 2: Ignore rows with no item_id
    if not item_id:
        continue

    # Rule 3: Deduplicate employee + item_id pairs
    dedupe_key = (employee_id, item_id)
    if dedupe_key in seen_employee_item_pairs:
        continue
    seen_employee_item_pairs.add(dedupe_key)

    parent_curriculum_title = parent_titles.get(parent_curriculum_id, "")

    record = {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "item_id": item_id,
        "item_title": item_title,
        "item_type": item_type,
        "subcurriculum_id": subcurriculum_id,
        "subcurriculum_title": subcurriculum_title,
        "parent_curriculum_id": parent_curriculum_id,
        "parent_curriculum_title": parent_curriculum_title
    }

    # -------------------------
    # Build left-side tree
    # -------------------------
    if parent_curriculum_id not in tree_map:
        tree_map[parent_curriculum_id] = {
            "parent_curriculum_id": parent_curriculum_id,
            "parent_curriculum_title": parent_curriculum_title,
            "subcurriculums": {}
        }

    parent_node = tree_map[parent_curriculum_id]

    if subcurriculum_id not in parent_node["subcurriculums"]:
        parent_node["subcurriculums"][subcurriculum_id] = {
            "subcurriculum_id": subcurriculum_id,
            "subcurriculum_title": subcurriculum_title,
            "items": {}
        }

    sub_node = parent_node["subcurriculums"][subcurriculum_id]

    if item_id not in sub_node["items"]:
        sub_node["items"][item_id] = {
            "item_id": item_id,
            "item_title": item_title,
            "item_type": item_type
        }

    # -------------------------
    # Build right-side lookup
    # -------------------------
    if item_id not in training_to_reports:
        training_to_reports[item_id] = []

    training_to_reports[item_id].append(record)

    # -------------------------
    # Build employee -> full training tree lookup
    # -------------------------
    if employee_id not in employee_training_map:
        employee_training_map[employee_id] = {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "tree_map": {}
        }

    emp = employee_training_map[employee_id]

    if parent_curriculum_id not in emp["tree_map"]:
        emp["tree_map"][parent_curriculum_id] = {
            "parent_curriculum_id": parent_curriculum_id,
            "parent_curriculum_title": parent_curriculum_title,
            "subcurriculums": {}
        }

    emp_parent = emp["tree_map"][parent_curriculum_id]

    if subcurriculum_id not in emp_parent["subcurriculums"]:
        emp_parent["subcurriculums"][subcurriculum_id] = {
            "subcurriculum_id": subcurriculum_id,
            "subcurriculum_title": subcurriculum_title,
            "items": {}
        }

    emp_sub = emp_parent["subcurriculums"][subcurriculum_id]

    if item_id not in emp_sub["items"]:
        emp_sub["items"][item_id] = {
            "item_id": item_id,
            "item_title": item_title,
            "item_type": item_type
        }

# =========================
# CONVERT TREE MAP TO LIST
# =========================
tree = []

for parent in tree_map.values():
    subcurriculum_list = []

    for sub in parent["subcurriculums"].values():
        item_list = list(sub["items"].values())
        item_list.sort(key=lambda x: x["item_title"].lower())

        subcurriculum_list.append({
            "subcurriculum_id": sub["subcurriculum_id"],
            "subcurriculum_title": sub["subcurriculum_title"],
            "items": item_list
        })

    subcurriculum_list.sort(key=lambda x: x["subcurriculum_title"].lower())

    tree.append({
        "parent_curriculum_id": parent["parent_curriculum_id"],
        "parent_curriculum_title": parent["parent_curriculum_title"],
        "subcurriculums": subcurriculum_list
    })

tree.sort(key=lambda x: x["parent_curriculum_title"].lower())

# =========================
# CONVERT EMPLOYEE TRAINING MAP TO LISTS
# =========================
employee_training_lookup = {}

for employee_id, employee_data in employee_training_map.items():
    employee_tree = []

    for parent in employee_data["tree_map"].values():
        subcurriculum_list = []

        for sub in parent["subcurriculums"].values():
            item_list = list(sub["items"].values())
            item_list.sort(key=lambda x: x["item_title"].lower())  # Rule 4

            subcurriculum_list.append({
                "subcurriculum_id": sub["subcurriculum_id"],
                "subcurriculum_title": sub["subcurriculum_title"],
                "items": item_list
            })

        subcurriculum_list.sort(key=lambda x: x["subcurriculum_title"].lower())

        employee_tree.append({
            "parent_curriculum_id": parent["parent_curriculum_id"],
            "parent_curriculum_title": parent["parent_curriculum_title"],
            "subcurriculums": subcurriculum_list
        })

    employee_tree.sort(key=lambda x: x["parent_curriculum_title"].lower())

    employee_training_lookup[employee_id] = {
        "employee_id": employee_id,
        "employee_name": employee_data["employee_name"],
        "tree": employee_tree
    }

# =========================
# FINAL JSON
# =========================
output = {
    "supervisor": {
        "name": SUPERVISOR_NAME,
        "email": SUPERVISOR_EMAIL
    },
    "tree": tree,
    "training_to_reports": training_to_reports,
    "employee_training_lookup": employee_training_lookup
}

# =========================
# WRITE JSON FILE
# =========================
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"Created {json_file}")

'''
In the HTML file, 

update this 
    const params = new URLSearchParams(window.location.search);
    const DATA_FILE = params.get("file");

    if (!DATA_FILE) {
    document.body.innerHTML = "<h2>No supervisor file specified.</h2>";
    throw new Error("Missing ?file= parameter");
    }

Swap with this
    const params = new URLSearchParams(window.location.search);
    const DATA_FILE = params.get("file") || "riley_magyar_data.json"; 
'''
    

