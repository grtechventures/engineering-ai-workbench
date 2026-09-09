# Third-party components

The Apache 2.0 license covers project contributions, not a relicensing of dependencies or external products.

- Bundled Three.js 0.180.0 and OrbitControls: MIT, copyright Three.js authors. The full notice is retained in `frontend/vendor/three/LICENSE`; provenance and the local-import modification are recorded in `PROVENANCE.json` there.
- Python dependencies are declared in `requirements.txt`, `requirements.lock` and the worker Dockerfile. Their distributions retain their own MIT, BSD, Apache, MPL, PSF and other applicable notices. Preserve the notices supplied by those distributions when packaging them.
- Docker Desktop, MATLAB, model weights and external services require their own licenses or entitlements. They are not granted by this repository's license and are not bundled here.
- Product names identify integrations or architectural options, not sponsorship or endorsement.
