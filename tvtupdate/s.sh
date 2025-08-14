#sudo cp -r /home/ck/Desktop/tvtupdate/ntp_face /home/ck/Desktop/
#sudo cp -r /home/ck/Desktop/tvtupdate/zj-guard-so /home/ck/Desktop/

### update ntp_face and zj-guard-so
cp -rf /usr/bin/zipx/zj-guard/tvtupdate/ntp_face /usr/bin/zipx/
cp -rf /usr/bin/zipx/zj-guard/tvtupdate/zj-guard-so /usr/bin/zipx/

### update zipx.ntp1.service
#cp /usr/bin/zipx/zj-guard/tvtupdate/zipx.ntp1.service /etc/systemd/system/
#sudo systemctl daemon-reload
#sudo systemctl enable zipx.ntp1.service
#sudo systemctl restart zipx.ntp1.service

# rv1126 version
/usr/bin/tvtservice restart zipx.ntp1.service
