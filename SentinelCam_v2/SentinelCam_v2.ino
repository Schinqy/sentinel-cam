#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

/*
 * SENTINELCAM ESP32 FIRMWARE v1.2 (Upgraded)
 * MJPEG Video Streaming + JSON API + Live Traffic Dashboard + Simulation Mode
 * 
 * --- CONFIGURATION ---
 * Replace placeholders with your actual network credentials
 */
const char* ssid = "Sch! Phone";
const char* password = "passc1d42";

// Camera Pinouts (AI-Thinker)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#define PART_BOUNDARY "123456789000000000000987654321"

static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// ================= SERVER HANDLES =================
httpd_handle_t stream_httpd = NULL;
httpd_handle_t api_httpd = NULL;

// ================= TRAFFIC STATE =================
String trafficState = "WAITING";

// ================= HANDLERS =================

// 1. MJPEG STREAM HANDLER (Original logic preserved)
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if(res != ESP_OK) return res;

  while(true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
    } else {
      _jpg_buf_len = fb->len;
      _jpg_buf = fb->buf;
    }

    if(res == ESP_OK) {
      size_t hlen = snprintf(part_buf, 64, _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if(res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    if(res == ESP_OK) res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));

    if(fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
    }

    if(res != ESP_OK) break;
  }
  return res;
}

// 2. ✅ NEW: JSON STATUS API (For Web App consumption)
static esp_err_t status_handler(httpd_req_t *req) {
  String json = "{\"state\":\"" + trafficState + "\"}";
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*"); // Important for Web App access
  return httpd_resp_send(req, json.c_str(), json.length());
}

// 3. ✅ NEW: SIMULATION ENDPOINT (/setstate?val=GREEN)
static esp_err_t set_state_handler(httpd_req_t *req) {
  char buf[64];
  size_t query_len = httpd_req_get_url_query_len(req) + 1;
  if (query_len > 1) {
    if (httpd_req_get_url_query_str(req, buf, query_len) == ESP_OK) {
      char param[32];
      if (httpd_query_key_value(buf, "val", param, sizeof(param)) == ESP_OK) {
        trafficState = String(param);
        trafficState.toUpperCase();
        Serial.println("SIMULATED_STATE: " + trafficState);
      }
    }
  }
  return httpd_resp_send(req, "OK", 2);
}

// 4. ✅ UPGRADED: LIVE TRAFFIC LIGHT PAGE (/trafficlights)
static esp_err_t traffic_handler(httpd_req_t *req) {
  String html = 
    "<!DOCTYPE html><html><head>"
    "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
    "<title>SENTINEL Live Status</title>"
    "<style>"
    "body{font-family:Arial,sans-serif;text-align:center;background:#111;color:white;padding-top:50px;}"
    ".box{font-size:40px;padding:30px;border:4px solid #fff;display:inline-block;border-radius:10px;min-width:200px;transition: 0.3s;}"
    ".RED{border-color:#ff4444; color:#ff4444; box-shadow: 0 0 20px #ff4444;}"
    ".GREEN{border-color:#44ff44; color:#44ff44; box-shadow: 0 0 20px #44ff44;}"
    ".YELLOW{border-color:#ffbb33; color:#ffbb33; box-shadow: 0 0 20px #ffbb33;}"
    "</style></head><body>"
    "<h1>Traffic Light State</h1>"
    "<div id='statusBox' class='box'>WAITING...</div>"
    "<p>Live UART data + Simulation Override</p>"
    "<script>"
    "function updateStatus() {"
    "  fetch('/status').then(res => res.json()).then(data => {"
    "    const box = document.getElementById('statusBox');"
    "    box.innerText = data.state;"
    "    box.className = 'box ' + data.state;"
    "  }).catch(err => console.error('Fetch error:', err));"
    "}"
    "setInterval(updateStatus, 500); // Update every 500ms"
    "</script>"
    "</body></html>";

  httpd_resp_set_type(req, "text/html");
  httpd_resp_send(req, html.c_str(), html.length());
  return ESP_OK;
}

// ================= CAMERA SERVER =================

void startCameraServer() {
  // 1. STREAM SERVER (Port 80)
  httpd_config_t stream_config = HTTPD_DEFAULT_CONFIG();
  stream_config.server_port = 80;
  stream_config.ctrl_port = 32768;

  // 2. API SERVER (Port 81)
  httpd_config_t api_config = HTTPD_DEFAULT_CONFIG();
  api_config.server_port = 81;
  api_config.ctrl_port = 32769; // Must be different
  api_config.max_open_sockets = 4;

  httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };
  httpd_uri_t status_uri = { .uri = "/status", .method = HTTP_GET, .handler = status_handler, .user_ctx = NULL };
  httpd_uri_t set_uri    = { .uri = "/setstate", .method = HTTP_GET, .handler = set_state_handler, .user_ctx = NULL };
  httpd_uri_t traffic_uri = { .uri = "/trafficlights", .method = HTTP_GET, .handler = traffic_handler, .user_ctx = NULL };

  // Start Stream Server
  if (httpd_start(&stream_httpd, &stream_config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }

  // Start API Server
  if (httpd_start(&api_httpd, &api_config) == ESP_OK) {
    httpd_register_uri_handler(api_httpd, &status_uri);
    httpd_register_uri_handler(api_httpd, &set_uri);
    httpd_register_uri_handler(api_httpd, &traffic_uri);
  }
}

// ================= SETUP =================

void setup() {
  Serial.begin(115200);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0; config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM; config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM; config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000; config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA; config.jpeg_quality = 15; config.fb_count = 1;

  esp_camera_init(&config);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  startCameraServer();

  Serial.print("Stream: http://"); Serial.print(WiFi.localIP()); Serial.println("/stream");
  Serial.print("API: http://");    Serial.print(WiFi.localIP()); Serial.println(":81/status");
  Serial.print("Live UI: http://"); Serial.print(WiFi.localIP()); Serial.println(":81/trafficlights");
}

// ================= LOOP =================

void loop() {
  while (Serial.available()) {
    String received = Serial.readStringUntil('\n');
    received.trim();
    if (received.length() > 0) {
      trafficState = received;
      trafficState.toUpperCase();
      Serial.println("STATE_UPDATED: " + trafficState);
    }
  }
  delay(10);
}
