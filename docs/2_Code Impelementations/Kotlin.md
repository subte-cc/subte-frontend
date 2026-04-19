# Kotlin Implementation
*Last Update: 18/04/2026*

```bash
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.URL
import javax.net.ssl.HttpsURLConnection

fun updateIPs(token: String, domain: String) {

        var connection: HttpsURLConnection
        val url = URL("https://subte.cc/up?domains=$domain") // Sets the url to make the request to

        connection = url.openConnection() as HttpsURLConnection
        connection.setRequestMethod("GET") // Sets request type to GET
        connection.setConnectTimeout(10000) // Sets connection timeout
        connection.setReadTimeout(10000) // Sets request response timeout
        connection.setRequestProperty("X-Api-Key", token) // Sets token as request header

        try {
            BufferedReader(InputStreamReader(connection.getInputStream())).use { `in` -> // Makes request
                val response = StringBuilder()
                var line: String?
                while ((`in`.readLine().also { line = it }) != null) {
                    response.append(line) 
                }
            }
        }catch(e: Exception){
        	// Code if request has failed goes here
        }
}
```