// svgo config used by `python3 -m pipeline.run` post-step / `pipeline/optimize.sh`.
// Keeps: viewBox, class names, data-* attrs, group structure (one <g> per colour).
export default {
  multipass: true,
  js2svg: { indent: 0, pretty: false },
  plugins: [
    { name: 'preset-default', params: { overrides: {
      removeViewBox: false, cleanupIds: false, removeMetadata: false, mergePaths: true, convertPathData: { floatPrecision: 2 },
      collapseGroups: false, removeUnknownsAndDefaults: { keepDataAttrs: true }, moveGroupAttrsToElems: false, moveElemsAttrsToGroup: false,
    } } },
    'removeDimensions',
  ],
};
