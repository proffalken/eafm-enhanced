# 🌊 EAFM-Enhanced: Environment Agency Flood Monitoring (Enhanced)

**EAFME** is a feature-rich, fork of the official Home Assistant Environment Agency integration.

While the original integration provides essential raw data, it could not support monitoring stations if they shared a name with other ones, which account for 8% of the total list.  **EAFME** is designed to provide actionable intelligence—telling you not just *how high* the river is, but what that level actually means for your local area.

---


## 🚀 Key Improvements in this Fork

### 1. 🆔 Fix: Duplicate Station Support

The original integration struggles with "Station Shadowing." If two or more stations share the same name (e.g., "The Weir"), the original integration will only display one, and it isn't at all clear which it is. 

**The solution:** I have used unique RLOI IDs and Catchment names in the selection process. This ensures that every single gauge in the UK is selectable, even if there are 10 others with the same name.  Needless to say that this also makes it much easier to find the station which you are looking for. 

### 2. 🔍 Enhancement: Each station is created as a 'device' and entities have extra attributes

I have configured it so that every added station via this integration is created as a 'device' with it's own entities within it.
On top of this,  the entity for the water level has now got extra attributes which you can use in other aspects of Home Assistant.   
These addtional attributes are

* **River** - Shows which river this monitoring station is on.
* **Catchment** - Shows which catchment area this monitoring station resides. 
* **Highest Recent Level** - The highest water level recorded "recently" (usually going back to when the station was installed on the river)
* **Highest Recent Date** - Date of which the above highest water level recorded was.
* **Typical High/Low Thresholds** - The levels at which the Environment Agency deem as being high (flooding/imminent) and low.

### 3. 🚦 Enhancement: Automated "River Status" Sensor

Since the API data includes the information for what is typical high and low heights for the water level, I have added a dedicated "Status" entity that calculates and categorizes the river's health in real-time:

* 🟢 **Normal**: Water levels are within the expected seasonal range.
* 🔴 **High**: Levels have exceeded the typical high threshold for this specific gauge. 
* 🟡 **Low**: Levels are below the typical low threshold.

With this you can easily create an automation to alert you if your local monitoring station is reporting as "high" as that usually means it is flooding, therefore you can plan alternative routes for travel etc. 

### 4. ✅❌ Enhancement: Dynamic Icons

Both of the entities created (Height & Status) have dynamic icons to give you a passing glance of if things are looking good or bad on your monitored station.  

* **Status** - Icon will be either a tick (check) if the levels are normal, or an exclamation mark if things are high/low.
* **Water level** - Icon will display as an upward or downward trending arrow to show you what the current trend based on the last couple of readings is.

---


### 5. 🚨 Enhancement: Flood Alert and Warning Areas

As well as river gauges, you can add Environment Agency **flood alert areas** and **flood warning areas**. Alert areas are wide and get early flood alerts; warning areas are smaller and get flood warnings and severe flood warnings.

When adding the integration, choose **Flood warning area**, give a point (it defaults to your Home Assistant location) and a search radius, then pick an area. Each area becomes a device with:

* **Flood warning** (sensor): `none`, `flood_alert`, `flood_warning` or `severe_flood_warning`. Attributes include the EA's `severity` text and `message`, `time_raised`, `time_severity_changed`, `time_message_changed`, the area's `county` and `river_or_sea`, and a `url` for the area's page on Check for flooding.
* **Flood warning in force** (binary sensor, safety): on while an alert or warning is in force.

Areas are checked every 5 minutes; the EA updates them every 15. A warning the EA has marked "no longer in force" counts as `none`.

Example automation:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.river_wye_in_gloucestershire_flood_warning
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "{{ state_translated(trigger.entity_id) }}: {{ state_attr(trigger.entity_id, 'area') }}"
      message: "{{ state_attr(trigger.entity_id, 'message') or 'No alert or warning in force.' }}"
```

---

## 🛠 Why Use This Over the Standard Version?

| Feature | Standard Integration | **EAFME (This Fork)** |
| --- | --- | --- |
| **Raw Water Levels** | ✅ | ✅ |
| **Handle Duplicate Names** | ❌ | ✅ |
| **River Status** (Normal/High/Low) | ❌ | ✅ |
| **Easier Configuration** | Label Only | Label + Catchment + ID |
| **Additional Attributes** | ❌ | ✅ |
| **Flood Alerts & Warnings** | ❌ | ✅ |

---


## ⚙️ Installation & Setup

1. **HACS:** Add this URL as a **Custom Repository** (Category: Integration).
2. **Install & Restart:** Download via HACS and restart Home Assistant.
3. **Configure:** Go to **Settings > Devices & Services > Add Integration** and search for **eafm enhanced**.

---


## 🙏 Credits & Acknowledgments

This project is a fork of the core [Environment Agency Flood Gauges](https://www.home-assistant.io/integrations/eafm/) integration.

* **Original Integration Author:** [Andrew Goddard (@Jc2k)](https://github.com/Jc2k).
* **Underlying Library:** Based on the `aioeafm` Python library.
* **Data Source:** This integration uses [Environment Agency flood and river level data](https://environment.data.gov.uk/flood-monitoring/doc/reference) from the real-time data API.

---


### 📝 Legal & Disclaimer

This integration is provided for informational purposes only. Data is sourced from the Environment Agency API (Open Government Licence v3.0). **Never rely solely on a smart home integration for life-safety decisions.** Always refer to the official [Check for Flooding](https://check-for-flooding.service.gov.uk/) service.

---


### Pro Dashboard Tip

You can now create a **Badge** on your Home Assistant dashboard that changes color based on the `sensor.[station]_river_status`. It makes it incredibly easy to see if you need to check the river at a single glance.

[Customizing Home Assistant Dashboards](https://www.google.com/search?q=https://www.youtube.com/watch%3Fv%3DkwLp99s_9Wc)

This video provides a great overview of how to customize your Home Assistant dashboard with custom sensors and states, perfect for making the most of your new River Status sensor.
