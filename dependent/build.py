import os
import platform
import subprocess


# 在参数dependentDir指定的目录下寻找参数filterBySuffix指定的类型文件，并以路径列表的形式返回
# 例如: findDependentFiles("D:/grandfather/father",(".c",))
# -father
#     -son
#         -main.c
#         -main.so
# 在如上目录结构下函数输出为['father/son/main.c']


def findDependentFiles(dependentDir, filterBySuffix=(".so", '.py', '.c')):
    n = len(dependentDir) - len(os.path.basename(dependentDir))
    files = os.walk(dependentDir)
    dependentFiles = []
    for i in files:
        currentFolderDirs, sonFolderNames, sonFileNames = i
        currentFolderDirs = currentFolderDirs[n:]
        for sfn in sonFileNames:
            if os.path.splitext(sfn)[1] in filterBySuffix:
                dependentFiles.append("/"+os.path.join(currentFolderDirs, sfn).replace("\\","/"))
    return dependentFiles


def build():
    # 输出路径设置在该py模块下
    platform_str = platform.platform()[0:15]
    print(f"platform={platform.platform()},platform_str={platform_str}")
    file_name = f"inside_{platform_str}.so"
    outputDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name).replace("\\", "/")
    # 终端命令将inside.c编译在outputDir下，并命名为inside_{平台信息}.so
    path_c_code = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inside.c")
    cmd = f'gcc -shared -fPIC {path_c_code} -o {outputDir}'
    print(f"cmd={cmd}")
    subprocess.run(cmd, shell=True)


if __name__ == "__main__":
    build()

