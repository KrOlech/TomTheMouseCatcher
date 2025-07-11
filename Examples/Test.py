import numpy as np
import matplotlib.pyplot as plt
import csv
import matplotlib.tri as tri

# Parametry konkursu
NUM_JURORS = 11
NUM_SUBCATEGORIES = 5
SCORE_RANGE = [0, 1, 2]
NUM_NOMINATED = 38
NUM_TRIALS = 1000
TOTAL_WORKS = 93  # całkowita liczba prac

# Funkcja: generuje ocenę jednej pracy
def simulate_scores(num_works):
    return np.random.randint(0, len(SCORE_RANGE), size=(num_works, NUM_JURORS, NUM_SUBCATEGORIES)).sum(axis=(1, 2))

results = []


a = 180
b = 197
c = 250

nomin_a, nomin_b, nomin_c = 0, 0, 0

for _ in range(NUM_TRIALS):
    scores_a = simulate_scores(a)
    scores_b = simulate_scores(b)
    scores_c = simulate_scores(c)

    all_scores = np.concatenate([scores_a, scores_b, scores_c])
    all_labels = (['A'] * a) + (['B'] * b) + (['C'] * c)

    top_indices = np.argpartition(-all_scores, NUM_NOMINATED)[:NUM_NOMINATED]
    top_labels = [all_labels[i] for i in top_indices]

    nomin_a += top_labels.count('A')
    nomin_b += top_labels.count('B')
    nomin_c += top_labels.count('C')

results.append([
    a, b, c,
    nomin_a / NUM_TRIALS,
    nomin_b / NUM_TRIALS,
    nomin_c / NUM_TRIALS
])

# Zapis wyników do CSV
with open("wyniki_symulacji.csv", "w", newline="", encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["a", "b", "c", "nom_a", "nom_b", "nom_c"])
    writer.writerows(results)

