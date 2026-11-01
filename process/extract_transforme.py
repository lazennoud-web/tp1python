import re #request : pour faire l extraction de la data de rows
from ingestion import raw


def extract_from_row(row):
    #w : letre chiffre ou _
    pattern=re.compile(r'\w{3}\s+(\d{2}\s+\d{2}:\d{2}:\d{2}).+:\s(\w+)')
    # le groupement est juste pour faciliter la lecture 
    match =re.search(pattern,row)
    if match : 
        print(f'month :{match.group(1)}\n day of month:{match.group(2)}\n'
              f'time :{match.group(3)}\n'
              f'message : {match.group(4)}\n'
              )
"""              
if __name__=="__main__":
    extract_from_row(raw,toRows('./data')[0])
def extract():
    rows =raw.toRows('./data')
    
    for row in rows: 
        pass  """
