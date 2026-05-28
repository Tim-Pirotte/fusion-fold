(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
  typeof define === 'function' && define.amd ? define(['exports'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.SVDJS = {}));
}(this, (function (exports) { 'use strict';
  var SVD = function SVD(a, withu, withv, eps, tol) {
    withu = withu !== undefined ? withu : true;
    withv = withv !== undefined ? withv : true;
    eps = eps || Math.pow(2, -52);
    tol = 1e-64 / eps;

    if (!a) {
      throw new TypeError('Matrix a is not defined');
    }


    var n = a[0].length;
    var m = a.length;

    if (m < n) {
      throw new TypeError('Invalid matrix: m < n');
    }

    var i, j, k, l, l1, c, f, g, h, s, x, y, z;
    g = 0;
    x = 0;
    var e = [];
    var u = [];
    var v = [];
    var mOrN = withu === 'f' ? m : n;

    for (i = 0; i < m; i++) {
      u[i] = new Array(mOrN).fill(0);
    }


    for (i = 0; i < n; i++) {
      v[i] = new Array(n).fill(0);
    }


    var q = new Array(n).fill(0);

    for (i = 0; i < m; i++) {
      for (j = 0; j < n; j++) {
        u[i][j] = a[i][j];
      }
    }

    for (i = 0; i < n; i++) {
      e[i] = g;
      s = 0;
      l = i + 1;

      for (j = i; j < m; j++) {
        s += Math.pow(u[j][i], 2);
      }

      if (s < tol) {
        g = 0;
      } else {
        f = u[i][i];
        g = f < 0 ? Math.sqrt(s) : -Math.sqrt(s);
        h = f * g - s;
        u[i][i] = f - g;

        for (j = l; j < n; j++) {
          s = 0;

          for (k = i; k < m; k++) {
            s += u[k][i] * u[k][j];
          }

          f = s / h;

          for (k = i; k < m; k++) {
            u[k][j] = u[k][j] + f * u[k][i];
          }
        }
      }

      q[i] = g;
      s = 0;

      for (j = l; j < n; j++) {
        s += Math.pow(u[i][j], 2);
      }

      if (s < tol) {
        g = 0;
      } else {
        f = u[i][i + 1];
        g = f < 0 ? Math.sqrt(s) : -Math.sqrt(s);
        h = f * g - s;
        u[i][i + 1] = f - g;

        for (j = l; j < n; j++) {
          e[j] = u[i][j] / h;
        }

        for (j = l; j < m; j++) {
          s = 0;

          for (k = l; k < n; k++) {
            s += u[j][k] * u[i][k];
          }

          for (k = l; k < n; k++) {
            u[j][k] = u[j][k] + s * e[k];
          }
        }
      }

      y = Math.abs(q[i]) + Math.abs(e[i]);

      if (y > x) {
        x = y;
      }
    }


    if (withv) {
      for (i = n - 1; i >= 0; i--) {
        if (g !== 0) {
          h = u[i][i + 1] * g;

          for (j = l; j < n; j++) {
            v[j][i] = u[i][j] / h;
          }

          for (j = l; j < n; j++) {
            s = 0;

            for (k = l; k < n; k++) {
              s += u[i][k] * v[k][j];
            }

            for (k = l; k < n; k++) {
              v[k][j] = v[k][j] + s * v[k][i];
            }
          }
        }

        for (j = l; j < n; j++) {
          v[i][j] = 0;
          v[j][i] = 0;
        }

        v[i][i] = 1;
        g = e[i];
        l = i;
      }
    }


    if (withu) {
      if (withu === 'f') {
        for (i = n; i < m; i++) {
          for (j = n; j < m; j++) {
            u[i][j] = 0;
          }

          u[i][i] = 1;
        }
      }

      for (i = n - 1; i >= 0; i--) {
        l = i + 1;
        g = q[i];

        for (j = l; j < mOrN; j++) {
          u[i][j] = 0;
        }

        if (g !== 0) {
          h = u[i][i] * g;

          for (j = l; j < mOrN; j++) {
            s = 0;

            for (k = l; k < m; k++) {
              s += u[k][i] * u[k][j];
            }

            f = s / h;

            for (k = i; k < m; k++) {
              u[k][j] = u[k][j] + f * u[k][i];
            }
          }

          for (j = i; j < m; j++) {
            u[j][i] = u[j][i] / g;
          }
        } else {
          for (j = i; j < m; j++) {
            u[j][i] = 0;
          }
        }

        u[i][i] = u[i][i] + 1;
      }
    }


    eps = eps * x;
    var testConvergence;

    for (k = n - 1; k >= 0; k--) {
      for (var iteration = 0; iteration < 50; iteration++) {
        testConvergence = false;

        for (l = k; l >= 0; l--) {
          if (Math.abs(e[l]) <= eps) {
            testConvergence = true;
            break;
          }

          if (Math.abs(q[l - 1]) <= eps) {
            break;
          }
        }

        if (!testConvergence) {
          c = 0;
          s = 1;
          l1 = l - 1;

          for (i = l; i < k + 1; i++) {
            f = s * e[i];
            e[i] = c * e[i];

            if (Math.abs(f) <= eps) {
              break;
            }

            g = q[i];
            q[i] = Math.sqrt(f * f + g * g);
            h = q[i];
            c = g / h;
            s = -f / h;

            if (withu) {
              for (j = 0; j < m; j++) {
                y = u[j][l1];
                z = u[j][i];
                u[j][l1] = y * c + z * s;
                u[j][i] = -y * s + z * c;
              }
            }
          }
        }

        z = q[k];

        if (l === k) {
          if (z < 0) {
            q[k] = -z;

            if (withv) {
              for (j = 0; j < n; j++) {
                v[j][k] = -v[j][k];
              }
            }
          }

          break;
        }


        x = q[l];
        y = q[k - 1];
        g = e[k - 1];
        h = e[k];
        f = ((y - z) * (y + z) + (g - h) * (g + h)) / (2 * h * y);
        g = Math.sqrt(f * f + 1);
        f = ((x - z) * (x + z) + h * (y / (f < 0 ? f - g : f + g) - h)) / x; // Next QR transformation

        c = 1;
        s = 1;

        for (i = l + 1; i < k + 1; i++) {
          g = e[i];
          y = q[i];
          h = s * g;
          g = c * g;
          z = Math.sqrt(f * f + h * h);
          e[i - 1] = z;
          c = f / z;
          s = h / z;
          f = x * c + g * s;
          g = -x * s + g * c;
          h = y * s;
          y = y * c;

          if (withv) {
            for (j = 0; j < n; j++) {
              x = v[j][i - 1];
              z = v[j][i];
              v[j][i - 1] = x * c + z * s;
              v[j][i] = -x * s + z * c;
            }
          }

          z = Math.sqrt(f * f + h * h);
          q[i - 1] = z;
          c = f / z;
          s = h / z;
          f = c * g + s * y;
          x = -s * g + c * y;

          if (withu) {
            for (j = 0; j < m; j++) {
              y = u[j][i - 1];
              z = u[j][i];
              u[j][i - 1] = y * c + z * s;
              u[j][i] = -y * s + z * c;
            }
          }
        }

        e[l] = 0;
        e[k] = f;
        q[k] = x;
      }
    }


    for (i = 0; i < n; i++) {
      if (q[i] < eps) q[i] = 0;
    }

    return {
      u: u,
      q: q,
      v: v
    };
  };
  var VERSION = '1.1.1';

  exports.SVD = SVD;
  exports.VERSION = VERSION;

  Object.defineProperty(exports, '__esModule', { value: true });

})));