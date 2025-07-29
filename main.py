from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import os
from dotenv import load_dotenv

from models import ScrapeRequest, ScrapeResponse, CredentialTestResponse
from reddit_scraper import RedditScraper

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Reddit Signal Scraper",
    description="Extract signals from Reddit subreddits, posts, and comments",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "message": "Reddit Signal Scraper API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "environment_variables": {
            "REDDIT_CLIENT_ID": bool(os.getenv("REDDIT_CLIENT_ID")),
            "REDDIT_CLIENT_SECRET": bool(os.getenv("REDDIT_CLIENT_SECRET")),
            "REDDIT_USER_AGENT": bool(os.getenv("REDDIT_USER_AGENT"))
        }
    }

@app.post("/test-credentials", response_model=CredentialTestResponse)
def test_credentials(request: ScrapeRequest):
    """Test endpoint to verify credential configuration"""
    config = request.config
    
    # Check what credentials are available
    has_config_client_id = bool(config.get('client_id') or config.get('clientId'))
    has_config_client_secret = bool(config.get('client_secret') or config.get('clientSecret'))
    has_config_user_agent = bool(config.get('user_agent') or config.get('userAgent'))
    
    has_env_client_id = bool(os.getenv('REDDIT_CLIENT_ID'))
    has_env_client_secret = bool(os.getenv('REDDIT_CLIENT_SECRET'))
    has_env_user_agent = bool(os.getenv('REDDIT_USER_AGENT'))
    
    return CredentialTestResponse(
        config_keys=list(config.keys()),
        has_config_credentials={
            "client_id": has_config_client_id,
            "client_secret": has_config_client_secret,
            "user_agent": has_config_user_agent
        },
        has_env_credentials={
            "client_id": has_env_client_id,
            "client_secret": has_env_client_secret,
            "user_agent": has_env_user_agent
        },
        credentials_source="environment" if (has_env_client_id and has_env_client_secret) 
                          else "config" if (has_config_client_id and has_config_client_secret)
                          else "none"
    )

@app.post("/scrape", response_model=ScrapeResponse)
def scrape(request: ScrapeRequest):
    """Main scraping endpoint"""
    try:
        print(f"📥 Received scrape request with {len(request.config.get('sources', []))} sources")
        
        # Create scraper instance
        scraper = RedditScraper(request.config)
        
        # Fetch data
        data = scraper.fetch_data()
        
        print(f"✅ Successfully scraped {len(data)} items")
        
        return ScrapeResponse(
            status="success",
            data=data,
            count=len(data),
            message=f"Successfully scraped {len(data)} items"
        )
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        print("❌ Exception during scrape:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Scraping failed: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for debugging"""
    print(f"❌ Unhandled exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
