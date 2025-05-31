# 🔒 Security Group Configuration Guide

## Step 1: Get Your Current IP Address

First, find your current public IP address:
```bash
curl ifconfig.me
```
**Write down this IP address - you'll need it for security group rules.**

## Step 2: Configure Security Groups in AWS Console

### 2.1 Access Security Groups
1. Go to **AWS Console** → **EC2** → **Security Groups** (left sidebar)
2. You'll see a list of security groups

### 2.2 Find Your Instance Security Groups
1. Click on **Instances** in the left sidebar
2. Find your ELK instance (`i-07849409590c08a3f`) and note its security group
3. Find your Honeypot instance (`i-0c876f3852ee6cb60`) and note its security group

### 2.3 Configure ELK Stack Security Group

1. Click on the security group attached to your ELK instance
2. Click **Edit inbound rules**
3. Add these rules (click **Add rule** for each):

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | [Your IP]/32 | SSH access |
| Custom TCP | TCP | 5601 | [Your IP]/32 | Kibana |
| Custom TCP | TCP | 9200 | [Honeypot SG ID] | Elasticsearch |
| Custom TCP | TCP | 5044 | [Honeypot SG ID] | Logstash |

**Important**: 
- Replace `[Your IP]` with your actual IP address from Step 1
- Replace `[Honeypot SG ID]` with the security group ID of your honeypot instance (starts with `sg-`)

### 2.4 Configure Honeypot Services Security Group

1. Click on the security group attached to your honeypot instance
2. Click **Edit inbound rules**
3. Add these rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | [Your IP]/32 | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP honeypot |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS honeypot |
| Custom TCP | TCP | 21 | 0.0.0.0/0 | FTP honeypot |
| Custom TCP | TCP | 23 | 0.0.0.0/0 | Telnet honeypot |
| Custom TCP | TCP | 25 | 0.0.0.0/0 | SMTP honeypot |
| Custom TCP | TCP | 2222 | 0.0.0.0/0 | SSH honeypot |
| Custom TCP | TCP | 3389 | 0.0.0.0/0 | RDP honeypot |
| Custom TCP | TCP | 12000 | [Your IP]/32 | Dashboard |

**Important**: Replace `[Your IP]` with your actual IP address from Step 1

## Step 3: Save Changes

1. Click **Save rules** for both security groups
2. Wait a few seconds for the changes to take effect

## Step 4: Test Connectivity

After configuring security groups, test SSH access:

```bash
# Test ELK instance
ssh -i ~/.ssh/honeypot-key.pem ubuntu@100.26.191.27

# Test Honeypot instance  
ssh -i ~/.ssh/honeypot-key.pem ubuntu@54.165.107.7
```

If you can connect successfully, you're ready to run the deployment script!

## Example Security Group Configuration

### ELK Stack Security Group Rules:
```
SSH          TCP  22    203.0.113.1/32     SSH access
Custom TCP   TCP  5601  203.0.113.1/32     Kibana
Custom TCP   TCP  9200  sg-0123456789abcdef0  Elasticsearch
Custom TCP   TCP  5044  sg-0123456789abcdef0  Logstash
```

### Honeypot Security Group Rules:
```
SSH          TCP  22    203.0.113.1/32     SSH access
HTTP         TCP  80    0.0.0.0/0          HTTP honeypot
HTTPS        TCP  443   0.0.0.0/0          HTTPS honeypot
Custom TCP   TCP  21    0.0.0.0/0          FTP honeypot
Custom TCP   TCP  23    0.0.0.0/0          Telnet honeypot
Custom TCP   TCP  25    0.0.0.0/0          SMTP honeypot
Custom TCP   TCP  2222  0.0.0.0/0          SSH honeypot
Custom TCP   TCP  3389  0.0.0.0/0          RDP honeypot
Custom TCP   TCP  12000 203.0.113.1/32     Dashboard
```

## Troubleshooting

### Can't Connect via SSH?
1. Verify your IP address hasn't changed: `curl ifconfig.me`
2. Check that SSH rule uses your correct IP with `/32` suffix
3. Ensure instances are running in AWS Console
4. Try connecting from a different network/location

### Security Group Not Found?
1. Make sure you're in the correct AWS region
2. Check the instance details to see which security group is attached
3. Look for default security groups if custom ones aren't visible

### Still Can't Connect?
1. Check AWS CloudTrail for any access denied logs
2. Verify the SSH key file permissions: `ls -la ~/.ssh/honeypot-key.pem` (should show `-r--------`)
3. Try using verbose SSH: `ssh -v -i ~/.ssh/honeypot-key.pem ubuntu@100.26.191.27`

Once security groups are configured correctly, you can run the automated deployment script!