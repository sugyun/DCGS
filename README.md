# Divide and conquer framework for global stabilization (DCGS)
Find control sets for global stabilization of a target point attractor by finding optimal FVS subsets (canalizing sets) based on canalizing effect without considering monostability in each SCC and then combining them.
##### Please check "Tutorial_example.ipynb".

# Requirements
- python v3.x
- networkx v2.5
- sympy v1.4
- tarjan-0.2.3.2

# Install requirements
- pip install networkx==2.5
- conda install -c anaconda sympy
- pip install tarjan

Now clone this github repository and use it!

##### * We modified and used codes in CANA and PyBoolNet Python package. 

CANA: https://github.com/rionbr/CANA

PyBoolNet: https://github.com/hklarner/PyBoolNet


# References

An, S., Jang, S. Y., Park, S. M., Lee, C. K., Kim, H. M., & Cho, K. H. (2023). Global stabilizing control of large-scale biomolecular regulatory networks. Bioinformatics, 39(1), btad045.
https://academic.oup.com/bioinformatics/article/39/1/btad045/6998201
