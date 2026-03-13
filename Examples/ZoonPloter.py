from matplotlib import pyplot as plt
import matplotlib.patches as patches

zones = {}
zones["A"] = [105, 456, 207, 176]
zones["B"] = [343, 445, 592, 196]
zones["C"] = [954, 442, 544, 196]
zones["D"] = [1510, 456, 352, 168]
zones["E1"] = [1671, 663, 217, 72]
zones["E2"] = [1663, 345, 226, 72]
zones["F1"] = [1284, 660, 277, 176]
zones["F2"] = [1284, 238, 277, 176]
zones["G1"] = [586, 660, 664, 184]
zones["G2"] = [592, 236, 668, 182]
zones["H1"] = [120, 670, 431, 162]
zones["H2"] = [120, 240, 431, 162]
zones["S1"] = [1672, 740, 70, 89]
zones["S2"] = [1672, 247, 70, 89]

fig, ax = plt.subplots()

for key, item in zones.items():

    x, y, w, h = item



    print(x, y)

    rect = patches.Rectangle((x, y), w, h, linewidth=1, edgecolor='blue', facecolor='lightblue')
    ax.add_patch(rect)

    # Add name in top-right corner
    ax.text(x , y + h - 50, key, ha='left', va='bottom', fontsize=10, color='black')

ax.set_xlim(0, 1920)
ax.set_ylim(0, 1080)

#plt.show()

plt.savefig("Zoon_ref.png")
