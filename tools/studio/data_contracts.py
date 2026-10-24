"""Small typed field contracts, intentionally not an executable expression language."""
import math
from .graph import Invalid
from .workbench_data import public_field

TYPES={'any','string','number','boolean','object','array','null'}


def normalize(spec,default):
    rows=default if spec is None else spec
    if not isinstance(rows,list) or len(rows)>32:raise Invalid('数据合同最多声明 32 个字段')
    paths=set();result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)-{'field','type','required'}:raise Invalid('数据合同需要字段、类型与必需标记')
        path=public_field(row.get('field',''))
        if path in paths or row.get('type','any') not in TYPES or type(row.get('required',False)) is not bool:raise Invalid('数据合同字段重复、类型或必需标记无效')
        paths.add(path);result.append(dict(field=path,type=row.get('type','any'),required=row.get('required',False)))
    return result


def check(value,spec):
    for row in spec:
        actual=value;present=True
        for part in row['field'].split('.'):
            if not isinstance(actual,dict) or part not in actual:present=False;break
            actual=actual[part]
        if not present:
            if row['required']:raise Invalid('缺少必需输入/输出字段：'+row['field'])
            continue
        kind=row['type'];valid=(kind=='any' or kind=='string' and isinstance(actual,str) or kind=='number' and type(actual) in (int,float) and math.isfinite(actual) or kind=='boolean' and type(actual) is bool or kind=='object' and isinstance(actual,dict) or kind=='array' and isinstance(actual,list) or kind=='null' and actual is None)
        if not valid:raise Invalid('字段类型不匹配：'+row['field']+'，需要 '+kind)
