
import os, uvicorn
if __name__=="__main__":
    host=os.getenv("DASHBOARD_HOST","0.0.0.0"); port=int(os.getenv("DASHBOARD_PORT","8000"))
    uvicorn.run("app:app", host=host, port=port, reload=False)
