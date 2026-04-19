# API Specification
*Last Update: 17/04/2026*


## Protocol and Request Type
Subte.cc only offers support for HTTPS and GET requests to the following endpoint:
```bash
https://subte.cc/up?
```

## Supported Parameters

Multiple parameters can be specified separated by *&*


### Domains

Single domain update:
```bash
https://subte.cc/up?domains=YOURDOMAINHERE
```

Multiple subdomains separated by comma (,) can be updated with only one request:
```bash
https://subte.cc/up?domains=DOMAIN1,DOMAIN2,DOMAIN3,DOMAIN4,DOMAIN5
```


### IP

Specifies to which IP will the domains specified update to.
```bash
https://subte.cc/up?domains=YOURDOMAINHERE&ip=YOURIPHERE
```
*If the IP parameter is unspecified, the detected one from the request will be used.*


### Token as header (Recommended)

The user authentication token can be sent as the following header for added security:
```bash
X-Api-Key: YOURTOKENHERE
```
*(Case Sensitive)*


### Token (not reccommended, use headers instead)

Specifies the user authentication token
```bash
https://subte.cc/up?domains=YOURDOMAINHERE&token=YOURTOKENHERE
```
*Added for easy DuckDNS format compatibility, not recommended for security reasons.*

## Responses

If the GET request is successful it will return:
```bash
OK
```

If the GET request failed (Invalid parameters, Incorrect token, etc) it will return:
```bash
KO
```