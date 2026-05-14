import { useEffect, useState, useCallback } from 'react';

export interface ViolationEvent {
  type: string;
  cam_id: string;
  violation: string;
  confidence: number;
  timestamp: string;
  image_path?: string;
  plate_number?: string;
}

export const useSocket = (url: string) => {
  const [violations, setViolations] = useState<ViolationEvent[]>([]);
  const [trafficLight, setTrafficLight] = useState<string>('UNKNOWN');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let socket: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      console.log(`[Socket] Connecting to ${url}...`);
      socket = new WebSocket(url);

      socket.onopen = () => {
        console.log('[Socket] Connected');
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'STATUS') {
            setTrafficLight(data.traffic_light);
          } else if (data.type === 'SYSTEM_ARMED') {
            // This is handled by polling diagnostics in the main page,
            // but we could also expose it here if we wanted reactive state.
            // For now, let's just make sure it doesn't crash.
            console.log("[Socket] System Armed State:", data.armed);
          } else {
            setViolations((prev) => [data, ...prev].slice(0, 50)); // Keep last 50
          }
        } catch (error) {
          console.error('[Socket] Error parsing message:', error);
        }
      };

      socket.onclose = () => {
        console.log('[Socket] Disconnected. Reconnecting...');
        setIsConnected(false);
        reconnectTimeout = setTimeout(connect, 3000);
      };

      socket.onerror = (error) => {
        console.error('[Socket] Error:', error);
        socket.close();
      };
    };

    connect();

    return () => {
      if (socket) socket.close();
      clearTimeout(reconnectTimeout);
    };
  }, [url]);

  return { violations, trafficLight, isConnected };
};
