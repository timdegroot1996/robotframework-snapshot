@echo off
REM Run all acceptance tests in atest/robot/ with pabot. Results and test workspaces end up in results/.
REM ROBOT_PROCESSES: number of parallel processes, default 4. Extra arguments go to pabot, e.g. --test "Reference Run*"
if "%ROBOT_PROCESSES%"=="" set ROBOT_PROCESSES=4
pabot --testlevelsplit --processes %ROBOT_PROCESSES% --outputdir results %* atest\robot
exit /b %ERRORLEVEL%
