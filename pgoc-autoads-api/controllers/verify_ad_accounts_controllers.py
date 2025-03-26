import requests
from flask import jsonify
from models.models import db, User

FACEBOOK_GRAPH_API_URL = "https://graph.facebook.com/v22.0"

def get_facebook_user_id(access_token):
    """Validate access token and return Facebook user ID or error."""
    url = f"{FACEBOOK_GRAPH_API_URL}/me?access_token={access_token}"
    response = requests.get(url).json()
    if "error" in response:
        return None, response["error"]["message"]
    return response["id"], None

def get_ad_accounts(fb_user_id, access_token):
    """Get associated ad accounts for the Facebook user ID."""
    url = f"{FACEBOOK_GRAPH_API_URL}/{fb_user_id}/adaccounts?access_token={access_token}"
    response = requests.get(url).json()
    if "error" in response:
        return None, response["error"]["message"]
    return [acc["account_id"] for acc in response.get("data", [])], None

def get_facebook_pages(fb_user_id, access_token):
    """Get associated Facebook pages for the Facebook user ID."""
    url = f"{FACEBOOK_GRAPH_API_URL}/{fb_user_id}/accounts?access_token={access_token}"
    response = requests.get(url).json()
    if "error" in response:
        return None, response["error"]["message"]
    return [page["id"] for page in response.get("data", [])], None

def verify_ad_accounts(data):
    """Verify ad accounts, Facebook pages, and access tokens."""
    user_id = data.get("user_id")
    campaigns = data.get("campaigns", [])

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "Unauthorized: Not a user of Facebook-Marketing-Automation WebApp"}), 403

    access_token_map = {}
    verified_accounts = []

    grouped_campaigns = {}
    for campaign in campaigns:
        access_token = campaign.get("access_token")
        if access_token not in grouped_campaigns:
            grouped_campaigns[access_token] = []
        grouped_campaigns[access_token].append(campaign)

    for access_token, campaign_list in grouped_campaigns.items():
        ad_account_ids = [c["ad_account_id"] for c in campaign_list]
        facebook_page_ids = [c["facebook_page_id"] for c in campaign_list]

        if access_token not in access_token_map:
            fb_user_id, token_error = get_facebook_user_id(access_token)
            if token_error:
                access_token_map[access_token] = None
                for campaign in campaign_list:
                    verified_accounts.append({
                        "ad_account_id": campaign["ad_account_id"],
                        "ad_account_status": "Not Verified",
                        "ad_account_error": "Invalid access token",
                        "access_token": access_token,
                        "access_token_status": "Not Verified",
                        "access_token_error": token_error,
                        "facebook_page_id": campaign["facebook_page_id"],
                        "facebook_page_status": "Not Verified",
                        "facebook_page_error": "Invalid access token"
                    })
                continue
            access_token_map[access_token] = fb_user_id

        fb_user_id = access_token_map[access_token]
        if not fb_user_id:
            continue

        ad_accounts, ad_error = get_ad_accounts(fb_user_id, access_token)
        facebook_pages, page_error = get_facebook_pages(fb_user_id, access_token)
        
        for campaign in campaign_list:
            ad_account_id = campaign["ad_account_id"]
            facebook_page_id = campaign["facebook_page_id"]

            ad_account_status = "Verified" if ad_accounts and ad_account_id in ad_accounts else "Not Verified"
            ad_account_error = None if ad_account_status == "Verified" else "Ad account not associated with this access token"
            
            facebook_page_status = "Verified" if facebook_pages and facebook_page_id in facebook_pages else "Not Verified"
            facebook_page_error = None if facebook_page_status == "Verified" else "Facebook page not associated with this access token"

            verified_accounts.append({
                "ad_account_id": ad_account_id,
                "ad_account_status": ad_account_status,
                "ad_account_error": ad_account_error,
                "access_token": access_token,
                "access_token_status": "Verified",
                "access_token_error": None,
                "facebook_page_id": facebook_page_id,
                "facebook_page_status": facebook_page_status,
                "facebook_page_error": facebook_page_error
            })

    return jsonify({
        "user_id": user_id,
        "verified_accounts": verified_accounts
    })
