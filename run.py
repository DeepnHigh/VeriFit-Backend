import uvicorn
import os

if __name__ == "__main__":
    # 환경변수에서 포트 가져오기 (기본값: 8000)
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # reload 비활성화
        log_level="info"
    )
