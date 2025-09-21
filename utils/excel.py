import pandas as pd

def export_to_excel(notification, responses):
    data = []
    for r in responses:
        row = r.data
        row["user_id"] = r.user_id
        data.append(row)

    df = pd.DataFrame(data)
    filename = f"notification_{notification.id}.xlsx"
    df.to_excel(filename, index=False)
    return filename
