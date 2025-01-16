require 'webrick'
require 'newrelic_rpm'

# Configure New Relic Agent (usually done via newrelic.yml file)

# Define a basic HTTP server
class SimpleHTTPServer < WEBrick::HTTPServlet::AbstractServlet
  def do_GET(request, response)
    # Start a New Relic transaction for the request
    NewRelic::Agent::Tracer.in_transaction(name: 'HTTP_GET', category: :web) do
      # Add custom attributes globally
      NewRelic::Agent.add_custom_attributes(endpoint: request.path)

      # Start a custom segment for processing the request
      segment = NewRelic::Agent::Tracer.start_segment(name: 'ProcessRequest')
      begin
        # Add custom attributes for this segment
        NewRelic::Agent.add_custom_attributes(method: 'GET', path: request.path)

        # Generate the response
        response.status = 200
        response['Content-Type'] = 'text/plain'
        response.body = "Hello, world! You requested: #{request.path}"
      ensure
        # End the segment to record it
        segment.finish
      end
    end
  end
end

# Create the server
server = WEBrick::HTTPServer.new(Port: 8080)

# Mount the servlet
server.mount '/', SimpleHTTPServer

# Trap interrupt signals to gracefully shut down the server
trap 'INT' do
  Thread.new do
    puts "Shutting down server gracefully..."
    server.shutdown
    NewRelic::Agent.shutdown # Ensure New Relic agent shuts down properly
  end.join
end

# Start the server
server.start
