import whisper

model = whisper.load_model("medium")
result = model.transcribe(r"C:\Users\Zenbook\Downloads\MazeGrant.wav")
print(result["text"])