import os, shutil

deploy = r"D:\Web tools casio\casio-tools\deploy"
rac = r"C:\Users\ADMIN\Downloads\RAC-Compiler-main (1)\RAC-Compiler-main"
root = r"D:\Web tools casio\casio-tools"

# Copy static files
shutil.copy2(os.path.join(root, "index.html"), deploy)
shutil.copy2(os.path.join(root, "style.css"), deploy)

# Copy compiler folder
comp_dst = os.path.join(deploy, "compiler")
if os.path.exists(comp_dst):
    shutil.rmtree(comp_dst)
shutil.copytree(os.path.join(root, "compiler"), comp_dst, ignore=lambda s,f: [x for x in f if x.endswith(('.py', '.bat', '.js', 'bundle_compiler', 'gen_model_data', 'libcompiler_js', 'model_data'))])

# Copy libcompiler
lib_dst = os.path.join(deploy, "libcompiler")
if os.path.exists(lib_dst):
    shutil.rmtree(lib_dst)
shutil.copytree(os.path.join(rac, "libcompiler"), lib_dst)

# Copy model folders
for model in ["580vnx", "880btg"]:
    dst = os.path.join(deploy, model)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(rac, model), dst)

# Copy asm_ropchain
asm_dst = os.path.join(deploy, "asm_ropchain")
if os.path.exists(asm_dst):
    shutil.rmtree(asm_dst)
shutil.copytree(os.path.join(rac, "asm_ropchain"), asm_dst)

# requirements.txt
with open(os.path.join(deploy, "requirements.txt"), "w") as f:
    f.write("")

print("Deploy folder ready!")
print("Size:", sum(os.path.getsize(os.path.join(dp, f)) for dp,_,fn in os.walk(deploy) for f in fn), "bytes")