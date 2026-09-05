#!/usr/bin/env python3
"""Create a copyright-light writing-style reference from licensed Chinese creative corpora."""
from __future__ import annotations

import argparse, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

SPLIT = re.compile(r"(?:\r?\n){1,}|(?<=[。！？!?])")

def segments(text: str):
    for part in SPLIT.split(text):
        value = re.sub(r"\s+", " ", part).strip()
        # A reference unit can be a compact scene, turn, or paragraph; it is not labelled an essay.
        if 30 <= len(value) <= 1200:
            yield value

def load(root: Path):
    units=[]
    coig=json.loads((root/'coig-writer-all_human_data.json').read_text(encoding='utf-8'))
    for row in coig:
        for text in segments(row.get('answer','')):
            units.append(('COIG-Writer/Apache-2.0',text))
    for path in root.glob('creative-writing-*.jsonl'):
        for line in path.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            for message in row.get('messages',[]):
                if message.get('role')=='assistant':
                    for text in segments(re.sub(r'<think>[\s\S]*?</think>','',message.get('content',''))):
                        units.append(('creative_writing/MIT',text))
    return units

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source-root',type=Path,required=True); p.add_argument('--output-root',type=Path,required=True); p.add_argument('--target',type=int,default=10000); a=p.parse_args()
    seen=set(); rows=[]
    for source,text in load(a.source_root):
        digest=hashlib.sha256(text.encode()).hexdigest()
        if digest not in seen:
            seen.add(digest); rows.append((source,text,digest))
        if len(rows)>=a.target: break
    if len(rows)<a.target: raise SystemExit(f'Only {len(rows)} distinct eligible writing units; need {a.target}.')
    texts=[text for _,text,_ in rows]
    matrix=TfidfVectorizer(analyzer='char',ngram_range=(2,4),max_features=12000,min_df=3).fit_transform(texts)
    labels=MiniBatchKMeans(n_clusters=24,random_state=42,n_init=10,batch_size=512).fit_predict(matrix)
    a.output_root.mkdir(parents=True,exist_ok=True)
    index=[]; groups=defaultdict(list)
    for (source,text,digest),label in zip(rows,labels):
        item={'id':digest[:16],'source':source,'cluster':f'style-{label:02d}','chars':len(text),'first_person':text.count('我'),'question_marks':text.count('？')+text.count('?'),'exclamation_marks':text.count('！')+text.count('!'),'ending':text[-1:]}
        index.append(item); groups[label].append(item)
    (a.output_root/'writing-style-index.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in index)+'\n',encoding='utf-8')
    summary={'units':len(index),'clusters':24,'source_counts':dict(Counter(x['source'] for x in index)),'avg_chars':round(sum(x['chars'] for x in index)/len(index),1),'avg_first_person':round(sum(x['first_person'] for x in index)/len(index),2),'limitation':'This is a style-feature index from licensed creative corpora, not a database of New Concept contest essays and not a source for copying prose.'}
    (a.output_root/'writing-style-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__': main()
