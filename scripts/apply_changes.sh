#!/bin/bash
# このスクリプトを使えば、nginxとdaphneを再起動して、Django側の変更を反映できます。これで反映できないなら、collect staticできていないか、CDNを疑ってネ。

#Nginxとdaphneを再起動する
sudo systemctl daemon-reload
#sudo systemctl restart gunicorn.service
sudo systemctl restart daphne.service
sudo systemctl restart nginx.service

echo "nginxとdaphneを再起動、変更を反映しました。"
