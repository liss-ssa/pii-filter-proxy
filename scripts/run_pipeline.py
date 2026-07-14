import subprocess,sys

cmds=[[sys.executable,'scripts/generate_synthetic.py','--rows','2500','--seed','42'],[sys.executable,'scripts/evaluate.py'],[sys.executable,'-m','pytest']]
for cmd in cmds:
 print('>', ' '.join(cmd)); subprocess.run(cmd,check=True)
