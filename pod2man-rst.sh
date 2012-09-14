#! /bin/sh -x

./bin/simplevisor pod > man/simplevisor.pod

pod2man --section=1 --center="simplevisor man page" --release="" man/simplevisor.pod > man/simplevisor.1

./bin/simplevisor rst > docs/simplevisor-command.rst

pod2man --section=1 --center="simplevisor-control man page" --release="" bin/simplevisor-control > man/simplevisor-control.1

pod2man --section=1 --center="simplevisor-loop man page" --release="" bin/simplevisor-loop > man/simplevisor-loop.1

