import unicodedata, re

def normalize(s):
    # lowercase  
    s = s.lower()    

    # remove date if there
    expression = r"\(+[0-9]{4}\)+" # (date)
    if re.search(expression, s):
        s = s[:-6]

    # strip accents  
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    
    # remove non-alphanumeric & collapse whitespace  
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    return s