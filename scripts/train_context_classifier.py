from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

LABEL2ID = {"NOT_PII": 0, "PII": 1, "UNCERTAIN": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}


class ContextDataset(Dataset):
    def __init__(self, rows, tokenizer, max_length):
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        encoded = self.tokenizer(row["text"], truncation=True, max_length=self.max_length, padding="max_length", return_tensors="pt")
        return {k: v.squeeze(0) for k, v in encoded.items()} | {"labels": torch.tensor(LABEL2ID[row["label"]], dtype=torch.long)}


def read_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(model, loader, device):
    model.eval(); truth=[]; pred=[]; losses=[]
    with torch.inference_mode():
        for batch in loader:
            batch={k:v.to(device) for k,v in batch.items()}
            out=model(**batch); losses.append(float(out.loss.item()))
            truth.extend(batch["labels"].cpu().tolist()); pred.extend(out.logits.argmax(-1).cpu().tolist())
    p,r,f,_=precision_recall_fscore_support(truth,pred,average="macro",zero_division=0)
    return {"loss":sum(losses)/max(1,len(losses)),"accuracy":accuracy_score(truth,pred),"precision_macro":p,"recall_macro":r,"f1_macro":f,"classification_report":classification_report(truth,pred,target_names=[ID2LABEL[i] for i in range(3)],output_dict=True,zero_division=0)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",default="data/context/context_dataset.jsonl")
    ap.add_argument("--model-name",default="cointegrated/rubert-tiny2")
    ap.add_argument("--output",default="models/context-rubert-tiny2")
    ap.add_argument("--epochs",type=int,default=3)
    ap.add_argument("--batch-size",type=int,default=32)
    ap.add_argument("--lr",type=float,default=3e-5)
    ap.add_argument("--max-length",type=int,default=192)
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    random.seed(args.seed); torch.manual_seed(args.seed)
    rows=read_rows(Path(args.dataset)); random.shuffle(rows)
    n_test=max(1,int(len(rows)*.15)); n_val=max(1,int(len(rows)*.15))
    test=rows[:n_test]; val=rows[n_test:n_test+n_val]; train=rows[n_test+n_val:]
    tokenizer=AutoTokenizer.from_pretrained(args.model_name)
    model=AutoModelForSequenceClassification.from_pretrained(args.model_name,num_labels=3,label2id=LABEL2ID,id2label=ID2LABEL)
    device="cuda" if torch.cuda.is_available() else "cpu"; model.to(device)
    train_loader=DataLoader(ContextDataset(train,tokenizer,args.max_length),batch_size=args.batch_size,shuffle=True)
    val_loader=DataLoader(ContextDataset(val,tokenizer,args.max_length),batch_size=args.batch_size)
    test_loader=DataLoader(ContextDataset(test,tokenizer,args.max_length),batch_size=args.batch_size)
    optim=torch.optim.AdamW(model.parameters(),lr=args.lr)
    history=[]
    for epoch in range(1,args.epochs+1):
        model.train(); total=0.0
        for batch in train_loader:
            batch={k:v.to(device) for k,v in batch.items()}; optim.zero_grad(set_to_none=True)
            out=model(**batch); out.loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); optim.step(); total+=float(out.loss.item())
        metrics=evaluate(model,val_loader,device); metrics["epoch"]=epoch; metrics["train_loss"]=total/max(1,len(train_loader)); history.append(metrics)
        print(json.dumps({k:v for k,v in metrics.items() if k!="classification_report"},ensure_ascii=False))
    output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(output,safe_serialization=True); tokenizer.save_pretrained(output)
    test_metrics=evaluate(model,test_loader,device)
    report={"base_model":args.model_name,"device":device,"train_rows":len(train),"validation_rows":len(val),"test_rows":len(test),"history":history,"test":test_metrics}
    (output/"training_metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in test_metrics.items() if k!="classification_report"},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
