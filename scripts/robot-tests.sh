#!/usr/bin/env bash
# Run all acceptance tests in atest/robot/ with pabot. Results and test workspaces end up in results/.
# ROBOT_PROCESSES: number of parallel processes, default 4. Extra arguments go to pabot, e.g. --test "Reference Run*"
pabot --testlevelsplit --processes "${ROBOT_PROCESSES:-4}" --outputdir results "$@" atest/robot
