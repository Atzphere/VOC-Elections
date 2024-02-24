import csv
# grab position table
fname = "../config/VOTING.csv"

with open(fname, newline='', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=',', quotechar='"',
                        quoting=csv.QUOTE_MINIMAL)
    columns = list(reader)[1:]
    f.close()
