# C# Implementation
*Last Update: 18/04/2026*

*Uses System.Net.Http library from .NET Framework 4.5 onwards*

```bash

static HttpClient client = new HttpClient(); // Creates a new HttpClient object

String domain = "YOURDOMAINHERE";
String token = "YOURTOKENHERE";

private async void updateip()
        {
            string url = "https://subte.cc/up?domains=" + domain; // Sets the url to make the request to
            client.DefaultRequestHeaders.Add("X-Api-Key", token); // Sets user token as request header
            try
            { 
               string response = await client.GetStringAsync(url); // Get request
            }
            catch (HttpRequestException ex)
            {
            	// Code if request has failed goes here
            }
```
