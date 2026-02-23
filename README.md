# Bank Marketing - Classification Analysis in R

## Description

This project contains a statistical and machine learning analysis applied to the **Bank Marketing** dataset (`bank-full.csv`). The goal is to build and compare several classification models to predict whether a customer will subscribe to a bank term deposit (target variable `y`).

## Dataset

The expected input file is `bank-full.csv` (semicolon-separated), typically available from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/ml/datasets/bank+marketing).

The main variables used in the analysis are:

| Variable | Description |
|----------|-------------|
| `y` | Target variable: did the client subscribe to a deposit? (`yes`/`no`) |
| `duration` | Duration of the last contact (seconds) |
| `poutcome` | Outcome of the previous campaign |
| `month` | Month of the last contact |
| `contact` | Type of contact |
| `housing` | Home mortgage |
| `job` | Type of job |
| `campaign` | Number of contacts during the campaign |
| `marital` | Marital status |
| `loan` | Personal loan in progress |
| `day` | Day of the last contact |
| `education` | Education level |

## Project Structure

```
├── Analisi_bank.R     # Main analysis script
├── bank-full.csv      # Dataset (to be added manually)
└── README.md
```

## Analysis Overview

### 1. Pre-processing
- Loading and inspecting the dataset
- Converting categorical variables to `factor`
- Checking for missing values (`NA`)

### 2. Exploratory Data Analysis (EDA)
- Interactive scatterplot matrix using `GGally` and `plotly`
- Bar charts and boxplots to explore relationships between variables and the target

### 3. Classification Models (Validation Set: 67% train / 33% test)

| Model | Description |
|-------|-------------|
| **Logistic Regression** | Stepwise variable selection (AIC), prediction threshold at 0.5 |
| **LDA** | Linear Discriminant Analysis, linear decision boundaries |
| **QDA** | Quadratic Discriminant Analysis, quadratic decision boundaries |

### 4. Cross-Validation (K-Fold with K=5)

| Model | Accuracy |
|-------|----------|
| Logistic Regression | ~90.2% |
| LDA | ~90.1% |
| KNN (k=9) | ~88.4% |

The best model is selected based on the minimum **Misclassification Error (MCE)**.

## R Libraries Used

```r
install.packages(c("ggplot2", "gridExtra", "plotly", "GGally", "MASS", "caret"))
```

## How to Run

1. Clone the repository and place the `bank-full.csv` file in the same folder as the script.
2. Open `Analisi_bank.R` in RStudio.
3. Run the script sequentially (libraries will be installed automatically on first run).

## Author

Project developed as an exercise in statistical analysis and supervised classification in R.
