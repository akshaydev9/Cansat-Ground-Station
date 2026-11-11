# Cansat-Ground-Station

# CanSat Ground Station

## Start the live dashboard

1. Connect the ground ESP32 receiver to the computer by USB.
2. In Windows Device Manager, find its COM port under **Ports (COM & LPT)**.
3. Open PowerShell in this folder and run:

   ```powershell
   py -m pip install -r requirements.txt
   py app.py
   ```

4. Open `http://127.0.0.1:5000`, enter the receiver COM port, and click **Connect**. The serial baud rate is set to the 115200 suggested in the project document.
5. To preview the interface without hardware, click **Start Demo** instead.

The browser page must be served by `app.py`; opening `index.html` directly does not connect to the serial receiver.

## Receiver packet format

The ground ESP32 should print one newline-terminated CSV packet per telemetry sample:

```text
team_id,time,count,altitude_m,pressure_hpa,temp_c,voltage_v,latitude,longitude,gnss_time,gnss_altitude_m,satellites,accel_xyz,roll|pitch|yaw,flight_state_index,extra
```

The first 15 fields are required by the dashboard. Flight-state indexes are `0=BOOT`, `1=TEST_MODE`, `2=LAUNCH_PAD`, `3=ASCENT`, `4=ROCKET_DEPLOY`, `5=DESCENT`, `6=AEROBREAK_RELEASE`, and `7=IMPACT`. Use `NA` for unavailable GPS values; do not send a fabricated coordinate.

Enter the known drop/release latitude and longitude in decimal degrees in the map controls and click **Set Drop Point**. Live GPS fixes then update the vehicle marker and recovery trail separately. If the team has no measured release coordinate, the first valid GPS fix can be viewed on the map, but it should not be presented as the exact release point.
