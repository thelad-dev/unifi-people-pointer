# Deployment Guide - UniFi People Pointer v1.0.0

## Release Status

✅ **v1.0.0 Released** - 2026-08-15

## GitHub Release

- **Tag**: v1.0.0
- **Release**: https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v1.0.0
- **Pull Request**: https://github.com/thelad-dev/unifi-people-pointer/pull/4

## HACS Ready ✅

The integration is ready for HACS submission:

- ✅ `hacs.json` configured
- ✅ `info.md` for HACS display
- ✅ Proper repository structure
- ✅ Versioned manifest.json (1.0.0)
- ✅ Valid Home Assistant integration

### HACS Submission (Optional Next Step)

To submit to HACS default repository:

1. Fork https://github.com/hacs/default
2. Add entry to `custom_components.json`:
   ```json
   {
     "unifi_people_pointer": {
       "name": "UniFi People Pointer",
       "country": ["DE"],
       "domains": ["device_tracker", "sensor"],
       "description": "Person-based presence detection via UniFi networks",
       "iot_class": "Local Polling",
       "homeassistant": "2024.1.0"
     }
   }
   ```
3. Create PR to HACS default repository

### Manual HACS Installation (Current)

Users can add custom repository:
1. HACS → Integrations → ⋮ → Custom repositories
2. Add: `https://github.com/thelad-dev/unifi-people-pointer`
3. Category: Integration
4. Click + and search "UniFi People Pointer"

## Webapp Deployment Ready ✅

Backend API is ready for deployment:

### Docker Deployment

```bash
# 1. Create .env file
cd backend
cp .env.example .env
# Edit .env with your settings

# 2. Build and run
cd ..
docker-compose up -d

# 3. Access
# API: http://localhost:3000
# Health: http://localhost:3000/health
```

### Manual Deployment

```bash
# 1. Install dependencies
cd backend
npm install

# 2. Build
npm run build

# 3. Configure
cp .env.example .env
# Edit .env

# 4. Run
npm start
```

### Environment Variables

Required:
- `HA_URL` - Home Assistant URL
- `HA_TOKEN` - Long-lived access token
- `UNIFI_URL` - UniFi Controller URL
- `UNIFI_API_KEY` - UniFi API key

Optional:
- `PORT` - Server port (default: 3000)
- `NODE_ENV` - Environment (production/development)

## Installation for Users

### Via HACS (Recommended when added to default)

1. Open HACS
2. Go to Integrations
3. Click +
4. Search "UniFi People Pointer"
5. Install

### Via Manual Download

1. Download from [Releases](https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v1.0.0)
2. Extract to `/config/custom_components/unifi_people_pointer`
3. Restart Home Assistant

### Configuration

1. Settings → Devices & Services → Add Integration
2. Search "UniFi People Pointer"
3. Enter UniFi Controller details
4. Configure polling settings
5. Edit `/config/unifi_people_pointer/people.json` to add people

## Documentation

- **README**: Bilingual (DE/EN) comprehensive guide
- **CHANGELOG**: Full version history
- **RELEASE_NOTES**: Detailed v1.0.0 release notes (DE/EN)
- **CONTRIBUTING**: Contribution guidelines
- **Examples**: Sample configuration files in `examples/`

## Support Channels

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support
- Repository: https://github.com/thelad-dev/unifi-people-pointer

## Next Release (v1.1.0 Planned)

- Device Tracker platform implementation
- Sensor platform with metrics
- Frontend UI (React/Vue)
- Extended zone support
- Bluetooth fallback

---

**Status**: ✅ RELEASE-READY
**Version**: 1.0.0
**Date**: 2026-08-15
