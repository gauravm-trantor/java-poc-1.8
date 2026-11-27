@echo off
rem Side-by-side: run setup-local.cmd from a given clone with JDK 8 and Maven on PATH but no Node.
rem It must stop at the Node check, before Docker. Usage: sbs-no-node.cmd <clone folder>
setlocal
set "JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-8.0.512.9-hotspot"
set "PATH=C:\WINDOWS\system32;C:\WINDOWS;C:\Tools\apache-maven-3.9.9\bin;%JAVA_HOME%\bin"
call "%~1\setup-local.cmd" < nul
echo exit=%errorlevel%
endlocal
