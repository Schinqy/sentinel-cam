
import time
import threading
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

# Simulated Global State
traffic_state = "IDLE"

# 1. Mock MJPEG Stream (Serves a static "video" frame)
def generate_frames():
    # This is a tiny 1x1 black pixel or a placeholder to simulate the stream
    # In a real test, we could load a sample image
    with open("mock_frame.jpg", "rb") as f:
        frame = f.read()
    
    while True:
        yield (b'--123456789000000000000987654321\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)  # 10 FPS

@app.route('/stream')
def stream():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=123456789000000000000987654321')

# 2. JSON Status API
@app.route('/status')
def status():
    response = jsonify({"state": traffic_state})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# 3. Simulation Endpoint (To change the state)
@app.route('/setstate')
def set_state():
    global traffic_state
    val = request.args.get('val', 'IDLE').upper()
    traffic_state = val
    return f"OK: {traffic_state}"

# 4. Live Dashboard (Exactly like the ESP32 code)
@app.route('/')
def dashboard():
    return """
    <!DOCTYPE html><html><head>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>SENTINEL Mock Server</title>
    <style>
    body{font-family:sans-serif;text-align:center;background:#0a0a0a;color:#fff;padding:20px;}
    .status-box{font-size:40px;padding:30px;border:4px solid #333;display:inline-block;border-radius:15px;transition:0.3s;min-width:200px;margin:20px;}
    .RED{border-color:#ff4444; color:#ff4444; text-shadow: 0 0 10px #ff4444;}
    .GREEN{border-color:#44ff44; color:#44ff44; text-shadow: 0 0 10px #44ff44;}
    .YELLOW{border-color:#ffbb33; color:#ffbb33; text-shadow: 0 0 10px #ffbb33;}
    </style></head><body>
    <h1>SENTINEL MOCK (Hardware Simulation)</h1>
    <div id='box' class='status-box'>LOADING...</div>
    <div style='margin-top:20px;'>
        <button onclick="fetch('/setstate?val=RED')">Simulate RED</button>
        <button onclick="fetch('/setstate?val=GREEN')">Simulate GREEN</button>
        <button onclick="fetch('/setstate?val=YELLOW')">Simulate YELLOW</button>
    </div>
    <script>
    function update(){
     fetch('/status').then(r=>r.json()).then(data=>{
      const el = document.getElementById('box');
      el.innerText = data.state;
      el.className = 'status-box ' + data.state;
     });
    }
    setInterval(update, 500);
    </script></body></html>
    """

if __name__ == '__main__':
    # Create a dummy frame if it doesn't exist
    import os
    if not os.path.exists("mock_frame.jpg"):
        from PIL import Image
        img = Image.new('RGB', (320, 240), color = (73, 109, 137))
        img.save('mock_frame.jpg')
        
    print("Mock ESP32 Cam running at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
