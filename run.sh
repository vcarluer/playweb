export FLASK_APP=playweb.py
if [[ "$1" == "--prod" ]]; then
	export FLASK_DEBUG=0
	HOST='127.0.0.1'
	PORT=4246
	nohup='nohup '
else
	export FLASK_DEBUG=1
	HOST='127.0.0.1'
	PORT=4246
	nohup=''
fi

${nohup}python3 -m flask run --port $PORT --host $HOST
