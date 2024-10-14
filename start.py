import uvicorn

if __name__ == "__main__":
    # Запуск приложения, которое находится в app.main
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
