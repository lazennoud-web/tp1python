import gzip

import os #ppur lire tt les fichiers 
"""
read data log from data directory as rows 
 """
def toRows(path):
    files=os.listdir(path)
    for file in files:
        file_path=path+'/'+file
        openner=gzip.open(filename=file_path, mode='rt',encoding='utf-8') if file.endswith('.gz') else open(file_path)
        with openner as f : 
            rows=f.readlines() #rows : variable qui reçoit les lignes lues.
    return rows
if __name__=="__main__":
        print(toRows('./data')[:10])

        
        """ gzip.open(file) if file.endswith('.gz') else open(file)
        if file.endswith('.gz') : 
            with gzip.open(file) as f : 
                pass
        else :
            with open(file) as f :
                pass  """