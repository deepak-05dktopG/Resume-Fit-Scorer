from fastapi import FastAPI


app = FastAPI(
	title="Resume to Job-Description Fit Scorer",
	description="An explainable API for evaluating resume fit against job descriptions.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
	return {
		"status": "ok",
		"service": "resume-fit-scorer",
	}
