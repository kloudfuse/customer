Edit `newrelic.yml` - enable only distributed tracing, and set the license_key

Set env variable:
`export NEW_RELIC_HOST=your.domain.com`

Run service:
`ruby server.rb`

Send request to server using:
`curl localhost:8080`

Traces should now be available under the "Traces" tab in Kloudfuse UI