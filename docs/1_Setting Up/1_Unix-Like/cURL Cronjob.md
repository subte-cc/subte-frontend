# Unix-Like with cURL
*Last Update: 15/04/2026*


## Single update with cURL

*Single Domain*
```bash
curl -H "X-Api-Key: YOURTOKENHERE" https://subte.cc/up?domains=YOURDOMAINNAMEHERE&ip=YOURIPHERE
```

*Multiple Domains*
```bash
curl -H "X-Api-Key: YOURTOKENHERE" https://subte.cc/up?domains=DOMAIN1,DOMAIN2&ip=YOURIPHERE
```
If no IP is specified in the request, the IP from where the request is made will be used.

*Only use subdomain wihout .subte.cc*

## Automatic updates using cron

*This requires cron be supported by your distro and installed on the system*

Open the crontab file with
```bash
crontab -e
```

Add the cronjob to the crontab file 
```bash
0 * * * *  curl -H "X-Api-Key: YOURTOKENHERE" https://subte.cc/up?domains=YOURDOMAINNAMEHERE&ip=YOURIPHERE
```
*This will update every every hour*

Update frequency can be adjusted by changing the 5 parameters, ordered by

```bash
*    *    *    *    *
|    |    |    |    |
|    |    |    |    |
|    |    |    |    |
|    |    |    | Day of week(0-6 | Sun-Sat)
|    |    |    |
|    |    |  Month(1-12)
|    |    |
|    |  Day of Month(1-31)
|    |
|   Hour(0-23)
|
Min(0-59)
```
