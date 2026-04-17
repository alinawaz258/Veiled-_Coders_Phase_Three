# GigShield AI

## About the Project

### Inspiration
India’s gig economy is scaling exponentially, employing over 15 million workers on platforms like Swiggy, Zomato, and Uber. Yet, this workforce remains incredibly financially fragile. During the monsoon seasons or times of civic unrest, one bad day of flooding doesn't just mean a minor inconvenience—it means a total loss of daily wages. Traditional insurance covers vehicle damage and hospitalization, but absolutely nothing covers the single most critical asset for gig workers: **their daily income flow**. We wanted to build a financial safety net for the gig economy that was robust, automatic, and frictionless.

### What it does
GigShield AI is India's first **parametric micro-insurance platform** targeted exclusively at loss-of-income for gig economy workers. Instead of waiting for riders to go through arduous manual claims processes after weeks of lost wages, our system relies on data to auto-trigger claims.

- **Dynamic Risk Profiling:** Riders submit their basic gig metrics (average hours, income) and their typical operating zone.
- **Parametric Payout Triggers:** If our Oracle Service detects objective environmental disruptions (e.g., rainfall exceeding $5\text{mm/hr}$ or a traffic congestion index $>85\%$), the policy triggers automatically.
- **Actuarial Machine Learning:** We use a Gradient Boosting Regressor (GBM) trained on synthetic gig worker profiles. The ML model is the primary decision-maker, predicting the probability of disruption using interactive features like $\text{rain} \times \text{flood}$ and emitting a hyper-localized ₹1–₹5 zone surcharge. 
- **Triple-Layer Fraud Detection:** We secure the ledger through 1) live kinematic GPS telemetry, 2) historical weather cross-referencing to prevent backdated claims, and 3) real-time Oracle API mismatch detection.

### How we built it
We developed the microservice around a standalone Python backend optimized to run anywhere, even in resource-constrained or low-connectivity environments. 
- The backend uses **FastAPI** to serve both the REST API and the static UI assets securely.
- The **ML Core** was written using `scikit-learn`'s `GradientBoostingRegressor` to ensure complex nonlinear relationships in our 16-feature vector were captured accurately.
- Our **Oracle Service** integrates directly with Open-Meteo and OpenStreetMap via a live signal layer, fetching localized weather metrics.
- The **Frontend UX** leverages beautiful, modern Tailwind CSS glassmorphism components with independent dual-dashboards: one representing the Rider's dynamic view, and the other detailing the Actuary/Admin KPIs (leveraging Chart.js for visualization).
- Finally, we integrated **Razorpay** (Sandbox mode) to execute UPI fund-account transfers, paired with an enhanced mock-UPI fallback generating timestamped UTRs to guarantee our demo never fails.

### Challenges we faced
1. **Actuarial Calibration:** Developing a premium pricing formula that stayed affordable for workers (₹22–₹80/week) while mathematically maintaining a sustainable $68\%-75\%$ loss-ratio for the insurer was difficult. We spent significant time mathematically modeling expected losses: 
   $$ E[\text{Loss}] = P(\text{disruption}) \times \text{Insured\_Cap} $$
2. **Combating Pricing Fraud:** We realized riders could manipulate input values (e.g., claiming to work 16 hours a day). We engineered a 6-signal fraud detection system to compute an anomaly score on the fly, inflating the premium or rejecting the underwriting request natively if suspicious activity was detected.
3. **Ensuring UI/UX Demo Reliability:** Integrating external APIs (weather/payments) in a hackathon often leads to broken demos. We engineered robust fallbacks for everything—if the frontend can't reach the Razorpay gateway, it gracefully falls back to our internal mock UPI generator.

### What we learned
We learned the profound difference between a standard ML classification script and an **actuarial risk engineering pipeline**. Structuring a machine learning codebase so that predictions feed harmoniously into a strictly bounded financial formula opened our eyes to the realities of InsurTech. We also learned how crucial "explainability" is: you cannot just deny a claim or boost a premium without showing the user exactly *why* (which is why our dashboard renders fractional pseudo-SHAP feature contributions!).

### What's next for GigShield AI
- **Blockchain Smart Contracts:** Migrating our parametric trigger engine to a Polygon/Ethereum smart contract to guarantee fully trustless, decentralized claim payouts.
- **Advanced Telematics:** Integrating mobile gyro and accelerometer data directly into the frontend capture flow to verify rider movement dynamically.
- **Pilot API Integrations:** Partnering directly with quick-commerce platforms (like Zepto or Blinkit) to abstract our insurance layers directly into their native fleet-management apps.


## Built With
FastAPI, Python, Scikit-learn, Tailwind CSS, Razorpay, Open-Meteo, HTML5, Chart.js, Uvicorn, Pandas, Numpy, Pydantic
