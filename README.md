# snapshotalyzer-3000

Demo project to manage AWS EC2 instance snapshots

## About

This project is a demo, and uses boto3 to manage AWS ec2 instance snapshots.

## COnfiguring

shotty uses the configuration file created by the
AWS cli
`aws configure --profile shotty`

## running

`pipenv run python shotty/shotty.py <command> <--project=PROJECT>`

_command_ is a list, start, or stop
_project_ is optional
