import re
SPLIT_COMMA = re.compile('\s*[,]+\s*')
SPLIT_SEMI = re.compile('\s*[;]+\s*')

PATTERN_LOCAL_IP = re.compile('127(\.\d{1,3}){3}$')