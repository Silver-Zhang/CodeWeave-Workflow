"""Bounded visible tool projections; never infer identity from name or order."""
from datetime import datetime
import json
import math
import re

def visible_content(value, _depth=0):
    """Unwrap public text blocks; never render thinking or transport wrappers."""
    if _depth>4:return '此工具没有可展示的文本结果；请核对原生证据。'
    for _ in range(2):
        if not isinstance(value,str):break
        try:value=json.loads(value)
        except (ValueError,RecursionError):break
    visible={'input_text','output_text','text'}
    blocks=visible|{'thinking','reasoning','image','image_url','input_image','output_image'}
    if isinstance(value,dict) and value.get('type') in ('tool_result','tool_use','function_call_output','custom_tool_call_output'):
        return visible_content(value.get('content',value.get('output','')), _depth+1)
    if isinstance(value,dict) and isinstance(value.get('type'),str) and value['type'] in blocks:value=[value]
    if isinstance(value,list) and any(isinstance(p,dict) and isinstance(p.get('type'),str) and p['type'] in blocks for p in value):
        text='\n'.join(p['text'] for p in value if isinstance(p,dict) and isinstance(p.get('type'),str) and p['type'] in visible and isinstance(p.get('text'),str))
        return text or '此工具没有可展示的文本结果；请核对原生证据。'
    return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)

def timestamp(value):
    if type(value) in (int, float):
        return value if math.isfinite(value) and 0<=value<=253402300799 else None
    if not isinstance(value, str):return None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError,OverflowError):return None

def group_tools(events):
    """Input is already redacted, public, budgeted events from ONE native session."""
    rows=[];by_id={}
    calls={'tool_use','function_call','custom_tool_call'}
    for event in events:
        key=event.get('call_id')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}',key):key=None
        row=by_id.get(key) if key else None
        if row is None:
            row=dict(name=event.get('name') or '工具结果',call_id=key,arguments=None,result=None,
                     started_at=None,finished_at=None,duration_seconds=None,
                     association='unknown',events=[],truncated=False)
            rows.append(row)
            if key:by_id[key]=row
        call=event['kind'] in calls;field='arguments' if call else 'result'
        text=event.get('content') or None
        if row[field] is not None and row[field]!=text:row['association']='conflict'
        else:row[field]=text
        if call:row['name']=event.get('name') or '工具调用'
        at=timestamp(event.get('at'))
        if call and row['started_at'] is None:row['started_at']=at
        if not call and row['finished_at'] is None:row['finished_at']=at
        row['events'].append(dict(kind=event['kind'],name=event.get('name'),content=text,at=at))
        row['truncated']|=event.get('truncated') is True
        if key and row['arguments'] is not None and row['result'] is not None and row['association']!='conflict':
            row['association']='matched'
            if row['started_at'] is not None and row['finished_at'] is not None and row['finished_at']>=row['started_at']:
                row['duration_seconds']=round(row['finished_at']-row['started_at'],6)
        # Keep the old readable content field for compatible history consumers.
        row['content']='\n'.join(v for v in (row['arguments'],row['result']) if isinstance(v,str))
    for row in rows:
        if row['association']=='conflict':row.update(arguments=None,result=None,duration_seconds=None,content='')
    if len(rows)>100:
        rows[-100]['history_truncated']=True
    return rows[-100:]
