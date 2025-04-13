import uvicorn
import sys
import argparse

if __name__ == "__main__":
    # CLI 인자 파서 생성
    parser = argparse.ArgumentParser(description='Run the FastAPI application with Uvicorn')
    
    # Uvicorn 설정 인자 추가
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes (default: 1)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to (default: 8000)')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload (development mode)')
    parser.add_argument('--log-level', type=str, default='info', 
                        choices=['critical', 'error', 'warning', 'info', 'debug', 'trace'],
                        help='Log level (default: info)')
    
    # 인자 파싱
    args = parser.parse_args()
    
    print(f"Starting server with {args.workers} worker(s) on {args.host}:{args.port}")
    print(f"Log level: {args.log_level}, Reload: {'enabled' if args.reload else 'disabled'}")
    
    # Uvicorn 실행
    uvicorn.run(
        "app.main:app", 
        host=args.host, 
        port=args.port, 
        workers=args.workers,
        reload=args.reload,
        log_level=args.log_level
    )