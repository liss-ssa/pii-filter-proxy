import argparse,csv,json,sys,time,statistics
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.detection.engine import DetectionEngine

def key(e):return (e['type'],e['start'],e['end'])
def pct(xs,p):
    xs=sorted(xs); return xs[min(len(xs)-1,int((len(xs)-1)*p))] if xs else 0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',default='data/synthetic/dataset.jsonl'); ap.add_argument('--report',default='reports/metrics.json'); ap.add_argument('--csv',default='reports/entity_metrics.csv'); a=ap.parse_args()
    rows=[json.loads(x) for x in Path(a.input).read_text(encoding='utf-8').splitlines() if x.strip()]
    eng=DetectionEngine(); tp=fp=fn=0; per=defaultdict(Counter); lat=[]; docs_with_leak=0; review_tp=review_fp=review_fn=0
    errors=[]
    for row in rows:
        t=time.perf_counter(); pred=eng.detect(row['text']); lat.append((time.perf_counter()-t)*1000)
        pred_c=[{'type':e.entity_type,'start':e.start,'end':e.end,'score':e.score} for e in pred if e.score>=.80]
        pred_u=[e for e in pred if .35<=e.score<.80]
        g={key(x) for x in row['entities']}; p={key(x) for x in pred_c}
        inter=g&p; tp+=len(inter); fp+=len(p-g); fn+=len(g-p)
        if g-p:docs_with_leak+=1
        for typ,s,e in inter:per[typ]['tp']+=1
        for typ,s,e in p-g:per[typ]['fp']+=1
        for typ,s,e in g-p:per[typ]['fn']+=1
        expected=bool(row.get('expected_review')); actual=bool(pred_u)
        if expected and actual:review_tp+=1
        elif actual and not expected:review_fp+=1
        elif expected and not actual:review_fn+=1
        if (p-g or g-p) and len(errors)<30:errors.append({'id':row['id'],'text':row['text'],'gold':sorted(g),'pred':sorted(p)})
    precision=tp/(tp+fp) if tp+fp else 1; recall=tp/(tp+fn) if tp+fn else 1; f1=2*precision*recall/(precision+recall) if precision+recall else 0
    rp=review_tp/(review_tp+review_fp) if review_tp+review_fp else 1; rr=review_tp/(review_tp+review_fn) if review_tp+review_fn else 1
    report={'dataset_rows':len(rows),'entities_gold':tp+fn,'true_positive':tp,'false_positive':fp,'false_negative':fn,'precision':precision,'recall':recall,'f1':f1,'document_leakage_rate':docs_with_leak/len(rows),'review_precision':rp,'review_recall':rr,'latency_ms':{'mean':statistics.mean(lat),'p50':pct(lat,.5),'p95':pct(lat,.95),'p99':pct(lat,.99)},'errors_sample':errors,'scope':'Synthetic rule-aligned evaluation; not evidence of real-world 99% quality.'}
    Path(a.report).parent.mkdir(parents=True,exist_ok=True); Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(a.csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['type','tp','fp','fn','precision','recall','f1']);w.writeheader()
        for typ,c in sorted(per.items()):
            p1=c['tp']/(c['tp']+c['fp']) if c['tp']+c['fp'] else 1;r1=c['tp']/(c['tp']+c['fn']) if c['tp']+c['fn'] else 1;f1t=2*p1*r1/(p1+r1) if p1+r1 else 0
            w.writerow({'type':typ,**c,'precision':p1,'recall':r1,'f1':f1t})
    print(json.dumps({k:v for k,v in report.items() if k!='errors_sample'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
