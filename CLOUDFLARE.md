# Cloudflare Configuration Guide

This document provides configuration recommendations for running the Journal App behind Cloudflare's proxy service.

## ✅ Implemented Features

### Real IP Detection
- Added `get_real_ip()` function in `security.py`
- Uses `CF-Connecting-IP` header for Cloudflare
- Falls back to standard proxy headers (`X-Forwarded-For`, `X-Real-IP`)
- Updated rate limiting to use real visitor IPs
- Updated security logging to show actual visitor IPs

## 🔧 Recommended Cloudflare Settings

### 1. SSL/TLS Configuration
- **SSL/TLS encryption mode**: Full (strict)
- **Always Use HTTPS**: ON
- **HTTP Strict Transport Security (HSTS)**: Enabled
- **Minimum TLS Version**: 1.2

### 2. Security Settings
- **Security Level**: Medium (adjust based on needs)
- **Bot Fight Mode**: ON
- **Browser Integrity Check**: ON
- **Challenge Passage**: 30 minutes

### 3. Speed Optimization
- **Auto Minify**: Enable CSS, HTML, JavaScript
- **Brotli**: ON
- **Rocket Loader**: OFF (can interfere with custom JS)
- **Mirage**: ON (for image optimization)

### 4. Caching Rules

#### Static Assets (Aggressive Caching)
```
Rule: Cache everything for static assets
If: URI Path contains "/static/"
Then: Cache Level = Cache Everything, Edge TTL = 1 month
```

#### API Endpoints (No Caching)
```
Rule: Bypass cache for API
If: URI Path starts with "/api/"
Then: Cache Level = Bypass
```

#### Dynamic Pages (Smart Caching)
```
Rule: Limited caching for authenticated areas
If: URI Path starts with "/journal/" OR "/dashboard"
Then: Cache Level = Bypass
```

### 5. Page Rules Priority Order
1. Bypass cache: `/api/*`
2. Bypass cache: `/journal/*` 
3. Bypass cache: `/dashboard/*`
4. Cache everything: `/static/*`

### 6. Security Headers (via Transform Rules)
```
Modify Response Header:
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
```

## 🚀 Performance Optimizations

### 1. Enable Cloudflare Features
- **Polish**: Lossless image compression
- **WebP conversion**: For supported browsers
- **HTTP/2**: Automatically enabled
- **HTTP/3 (QUIC)**: Enable if available

### 2. Worker Scripts (Optional)
Consider Cloudflare Workers for:
- Custom caching logic
- Request/response modification
- A/B testing
- Geographic redirects

## 🔒 Security Enhancements

### 1. WAF (Web Application Firewall)
- Enable managed rulesets
- Create custom rules for journal-specific attacks
- Monitor security events

### 2. Rate Limiting (Cloudflare Level)
```
Rate Limiting Rules:
- Login attempts: 5 per minute per IP
- API calls: 100 per minute per IP
- Form submissions: 10 per minute per IP
```

### 3. Access Control
- Use Cloudflare Access for admin areas if needed
- Implement country-based blocking if required
- Set up IP allowlists for administrative functions

## 📊 Monitoring and Analytics

### 1. Enable Analytics
- **Web Analytics**: For traffic insights
- **Security Analytics**: Monitor threats
- **Performance Analytics**: Track load times

### 2. Log Retention
- Configure log retention policies
- Export logs for analysis if needed
- Monitor error rates and response times

## 🔧 Application-Level Considerations

### 1. Trust Cloudflare IPs
The application is configured to trust Cloudflare's IP headers:
- `CF-Connecting-IP`: Real visitor IP
- `CF-Ray`: Request identifier
- `CF-Country`: Visitor country

### 2. CSRF Protection
Already configured for proxy environments:
```python
app.config['WTF_CSRF_SSL_STRICT'] = False
app.config['WTF_CSRF_CHECK_HEADERS'] = False
```

### 3. Session Security
- Sessions work correctly behind proxy
- Secure cookies are properly handled
- HTTPS redirects function properly

## 🎯 Testing Your Configuration

### 1. Verify Real IP Detection
Check logs to ensure real visitor IPs are recorded, not Cloudflare IPs.

### 2. Test Rate Limiting
Verify that rate limits apply per actual visitor, not per Cloudflare edge.

### 3. Security Headers
Use tools like securityheaders.com to verify header configuration.

### 4. Performance Testing
- Use Cloudflare's analytics to monitor performance
- Test from different geographic locations
- Verify caching is working for static assets

## 📋 Maintenance Tasks

### Regular Tasks
- Review Cloudflare analytics monthly
- Update security rules based on threat landscape
- Monitor error rates and performance metrics
- Review and optimize caching rules

### Security Monitoring
- Check WAF events weekly
- Review rate limiting effectiveness
- Monitor for new attack patterns
- Update IP allowlists as needed

## 🆘 Troubleshooting

### Common Issues
1. **Real IP not detected**: Check CF-Connecting-IP header
2. **Rate limiting not working**: Verify get_real_ip() function
3. **CSRF errors**: Check proxy SSL configuration
4. **Caching issues**: Review page rules and cache levels

### Debug Commands
```bash
# Check headers received by application
curl -H "CF-Connecting-IP: 1.2.3.4" https://journal.joshsisto.com/

# Test rate limiting
# (Make multiple requests quickly to verify limiting works)

# Verify SSL configuration
openssl s_client -connect journal.joshsisto.com:443
```

## 📞 Support

For Cloudflare-specific issues:
- Cloudflare Support Center
- Community Forums
- Documentation: https://developers.cloudflare.com/

For application-specific issues:
- Check application logs
- Review security.py configuration
- Test with real IP detection