from app import app
from config import Config

# app.run(host,port,debug,options)
# host - 要监听的主机名
# port - 默认值为5000
# debug - 默认为false
app.run(debug = Config.DEBUG)
