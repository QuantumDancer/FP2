#!/usr/bin/python

__author__ = "Benjamin Rottler (benjamin@dierottlers.de)"

import os
from numpy import sqrt, mean
from op import OPData, prepareGraph, avgCloseValues, getRootColor
from functions import setupROOT, compare2Floats
from data import DataErrors
from fitter import Fitter
from txtfile import TxtFile
from ROOT import TCanvas, TLegend

DIR = '../data/part2/04.16/'
ETALON_XMINMAX = {'up-etalon_zoom.tab': (0.78e-3, 8.5e-3), 'down-etalon_zoom.tab': (3e-3, 8.5e-3)}
PEAKS_XMINMAX = {'up-hfs_zoom.tab': (0.4e-3, 1.7e-3), 'down-hfs_zoom.tab': (0.5e-3, 1.6e-3)}


def makeSingleGraph(file, save=True):
    ch1 = OPData.fromPath(DIR + file, 1)
    ch2 = OPData.fromPath(DIR + file, 2)

    c = TCanvas('c' + file, '', 1280, 720)
    g1 = ch1.makeGraph('g1' + file[:-4], 't / s', 'U / V')
    prepareGraph(g1)
    g1.GetXaxis().SetRangeUser(ch1.getMinX(), ch1.getMaxX())
    g1.SetMinimum(min(ch1.getMinY(), ch2.getMinY()) * 1.1)
    g1.SetMaximum(max(ch1.getMaxY(), ch2.getMaxY()) * 1.1)
    g2 = ch2.makeGraph('g2' + file[:-4])
    prepareGraph(g2, 2)

    g1.Draw('APX')
    g1.Draw('P')
    g2.Draw('PX')
    g2.Draw('P')
    c.Update()
    if save:
        c.Print('../img/part2/%s.pdf' % file[:-4], 'pdf')
    return ch1, ch2, c, g1, g2


def makeGraphs():
    for file in os.listdir(os.path.join(os.getcwd(), DIR)):
        if file.endswith('.tab'):
            makeSingleGraph(file)


def getApproxEtalonMaxima(ch, xmin, xmax):
    chrebin = ch.rebin(5)
    ch2max = chrebin.findExtrema(15, xmin, xmax, False).getX()
    return avgCloseValues(ch2max, 10 * ch.getMinDeltaX())  # combine peaks which are closer than epsilon together


def fitEtalonPeak(g, peakx, deltaX, i, name, isUp=True):
    print('fit etalon peak %s: %.4f +- %.5f' % (name, peakx, deltaX))
    fit = Fitter('%s-peak%d' % (name, i), '[0]+[1]*x+[2]*TMath::CauchyDist(x, [3], [4])')
    fit.function.SetLineColor(getRootColor(i))
    fit.setParam(0, 'a', 0)
    b = 50
    if isUp:
        fit.setParam(1, 'b', b)
        fit.setParamLimits(1, 0, 4 * b)
    else:
        fit.setParam(1, 'b', -b)
        fit.setParamLimits(1, -b * 4, 0)
    fit.setParam(2, 'A', 2e-5)
    fit.setParamLimits(2, 0, 1)
    fit.setParam(3, 'x', peakx)
    fit.setParamLimits(3, peakx - deltaX, peakx + deltaX)
    fit.setParam(4, 's', 1e-4)
    fit.setParamLimits(4, 0, 5e-3)
    fit.fit(g, peakx - deltaX, peakx + deltaX, '+')
    fit.saveData('../fit/part2/%s-peak%d.txt' % (name, i))
    return (fit.params[3]['value'], 0.2 * fit.params[4]['value']), fit.function


def fitLaserVoltage(g, xmin, xmax, file):
    fit = Fitter('%s-laser' % file[:-4], 'pol1(0)')
    fit.function.SetLineColor(92)
    fit.function.SetLineWidth(2)
    fit.setParam(0, 'a', 0)
    fit.setParam(1, 'b', 100)
    fit.fit(g, xmin, xmax, '+')
    fit.saveData('../fit/part2/%s-laser.txt' % file)
    return (fit.params[1]['value'], fit.params[1]['error'], fit.function)


def makePeakFreqGraph(peaks, name):
    xlist = list(list(zip(*peaks))[0])
    sxlist = list(list(zip(*peaks))[1])
    ylist = list(map(lambda i: i * 9.924, range(len(peaks))))
    sylist = list(map(lambda i: i * 0.03, range(len(peaks))))

    direction = name.split('-')[0]
    tabledata = list(zip(*[list(range(1, len(xlist) + 1)), list(map(lambda x:x * 1000, xlist)), list(map(lambda x:x * 1000, sxlist)),
                           ylist, sylist]))
    with TxtFile('../src/tab_part2_etalonfreqs_%s.tex' % direction, 'w') as f:
        f.write2DArrayToLatexTable(tabledata,
                                   ["i", r"$x_i$ / s", r"$0.2 \cdot s_i$ / s", r"$\nu_i$ / GHz", r"$s_{\nu_i}$ / GHz"],
                                   ["%d", "%.3f", "%.3f", "%.2f", "%.2f"],
                                   "Zentren $x_i$ der gefitteten Cauchy-Funktionen mit abgeschätztem Fehler aus den " +
                                   "Breiteparametern $s_i$ und Frequenzdifferenzen zum ersten Peak. ",
                                   "tab:etalon:calib:%s" % direction)

    etalonData = DataErrors.fromLists(xlist, ylist, sxlist, sylist)
    etalonData.multiplyX(1000)
    c = TCanvas('c_pf_' + name, '', 1280, 720)
    g = etalonData.makeGraph('g_pf_' + name, 't / ms', '#Delta#nu / GHz')
    g.SetMinimum(etalonData.getMinY() - 5)
    g.SetMaximum(etalonData.getMaxY() + 5)
    g.Draw('AP')

    fit = Fitter('fit_pf_' + name, 'pol1(0)')
    fit.setParam(0, 'a')
    fit.setParam(1, 'b')
    xmin, xmax = etalonData.getMinX(), etalonData.getMaxX()
    deltax = (xmax - xmin) / 10
    fit.fit(g, xmin - deltax, xmax + deltax)
    fit.saveData('../fit/part2/%s-etalon_calibration.txt' % name)

    if fit.params[1]['value'] < 0:
        l = TLegend(0.575, 0.6, 0.85, 0.85)
    else:
        l = TLegend(0.15, 0.6, 0.425, 0.85)
    l.SetTextSize(0.03)
    l.AddEntry(g, 'Etalonpeaks', 'p')
    l.AddEntry(fit.function, 'Fit mit #Delta#nu = a + b * t', 'l')
    fit.addParamsToLegend(l, [('%.2f', '%.2f'), ('%.2f', '%.2f')], chisquareformat='%.2f', units=('GHz', 'GHz/ms'))
    l.Draw()

    c.Update()
    c.Print('../img/part2/%s-etalon_calibration.pdf' % name, 'pdf')

    return (fit.params[1]['value'], fit.params[1]['error'])


def fitSingleEtalonFile(file):
    ch1, ch2, c, g1, g2 = makeSingleGraph(file, False)
    xmin, xmax = ETALON_XMINMAX[file]
    isUp = file[:2] == 'up'

    etalonPeaksStartX = getApproxEtalonMaxima(ch2, xmin, xmax)
    if file[:2] == "up":
        etalonPeaksStartX = etalonPeaksStartX[2:-1]
    elif file[:4] == "down":
        etalonPeaksStartX = etalonPeaksStartX[:-1]
    peakfits = []
    fitfuncs = []
    deltaX = ch2.getMinDeltaX() * 30
    name = file[:-4]
    for i, peak in enumerate(etalonPeaksStartX):
        peakfit, fitfunc = fitEtalonPeak(g2, peak, deltaX, i, name, isUp)
        peakfits.append(peakfit)
        fitfuncs.append(fitfunc)

    laserslope, slaserslope, laserfunc = fitLaserVoltage(g1, xmin, xmax, file)

    if isUp:
        l = TLegend(0.65, 0.13, 0.99, 0.47)
    else:
        l = TLegend(0.125, 0.13, 0.475, 0.45)
    l.SetTextSize(0.03)
    l.AddEntry(g1, 'Spannung der Lasermodulation', 'l')
    l.AddEntry(g2, 'Etalonspektrum', 'l')
    for i, func in enumerate(fitfuncs):
        l.AddEntry(func, 'Fit des %d. Peaks mit Cauchy + lin. Ug.' % (i + 1), 'l')
    l.AddEntry(laserfunc, 'Fit mit Gerade', 'l')
    l.Draw()

    c.Update()
    c.Print('../img/part2/%s_fit.pdf' % name, 'pdf')

    return peakfits, (laserslope, slaserslope)


def evalEtalonData():
    files = os.listdir(os.path.join(os.getcwd(), DIR))
    freqCalibration = dict()
    for file in filter(lambda s: 'etalon_zoom' in s, files):
        print('eval ' + file)
        peaks, laser = fitSingleEtalonFile(file)
        freqCalibration[file.split('-')[0]] = makePeakFreqGraph(peaks, file[:-4])  # GHz / ms
    return freqCalibration


def makeHFSGraph(name, xmin, xmax):
    ch1 = OPData.fromPath('../data/part2/%s.tab' % name, 1)
    ch2 = OPData.fromPath('../data/part2/%s.tab' % name, 2)
    ch1.multiplyX(1000)
    ch2.multiplyX(1000)

    c = TCanvas('c-%s' % name, '', 1280, 720)

    g1 = ch1.makeGraph('g1-%s' % name, 't / ms', 'U / V')
    prepareGraph(g1)
    g1.SetMinimum(min(ch2.getY()) * 1.2)
    g1.SetMaximum(max(ch2.getY()) * 1.2)
    g1.GetXaxis().SetRangeUser(xmin, xmax)
    g1.Draw('APX')
    g2 = ch2.makeGraph('g2-%s' % name)
    prepareGraph(g2)
    g2.SetMarkerColor(2)
    g2.Draw('PX')

    fitStartParams = getHFSFitStartParams(name)
    fitres = []
    if fitStartParams:
        peakNum = 0
        offset = ch2.getY()[0]  # approx offset of underground
        slope = (ch2.getY()[-1] - ch2.getY()[0]) / (xmax - xmin)  # approx slope of underground
        for peakparams, xstartend in fitStartParams:
            xstart, xend = xstartend
            peakcount = len(peakparams)
            fitfunc = 'pol1(0)+gaus(2)'
            dpc = 2  # delta param count
            for i in range(1, peakcount):
                fitfunc += '+gaus(%d)' % (i * 3 + dpc)
            fit = Fitter('fitHFS%s' % name, fitfunc)
            fit.function.SetLineColor(peakNum + 3)
            fit.setParam(0, 'a', offset)
            fit.setParamLimits(0, 0, offset * 2)
            fit.setParam(1, 'b', slope)
            fit.setParamLimits(1, 0, 2 * slope)
            for i, params in enumerate(peakparams):
                fit.setParam(i * 3 + dpc, 'A%d' % i, params[0])
                fit.setParam(i * 3 + dpc + 1, 'c%d' % i, params[1])
                fit.setParam(i * 3 + dpc + 2, 's%d' % i, params[2])
                if params[0] < 0:
                    fit.setParamLimits(i * 3 + dpc, 3 * params[0], 0)
                else:
                    fit.setParamLimits(i * 3 + dpc, 0, 2 * params[0])
                fit.setParamLimits(i * 3 + dpc + 1, params[1] - 2 * params[2], params[1] + 2 * params[2])
                fit.setParamLimits(i * 3 + dpc + 2, 0, 20 * params[2])
            fit.fit(g2, xstart, xend, '+')
            fit.saveData('../fit/part2/%s-%d.txt' % (name, peakNum))
            for i in range(len(peakparams)):
                fitres.append((fit.params[i * 3 + dpc + 1]['value'], fit.params[i * 3 + dpc + 1]['error']))
            peakNum += 1

    g1.Draw('P')
    g2.Draw('P')
    c.Update()
    c.Print('../img/part2/%s_fit.pdf' % name, 'pdf')
    return fitres


def getHFSFitStartParams(name):
    params = dict()
    params['up-hfs_zoom'] = [[[(-0.1715, 0.0005724, 8.151e-6), (-0.0639, 0.0006404, 5.15e-6)], (0.0005191, 0.0007188)],
                             [[(-0.4311, 0.000874, 11.25e-6)], (0.0008218, 0.0009425)],
                             [[(-0.6082, 0.001222, 9e-6), (-0.2959, 0.001295, 25e-6), (-0.2296, 0.001394, 22e-6)], (0.001145, 0.001436)]]
    params['down-hfs_zoom'] = [[[(-0.1396, 0.0006458, 4.45e-6), (-0.1496, 0.0007232, 8.15e-6), (-0.4065, 0.0008303, 4.45e-6)], (0.0006026, 0.0009166)],
                               [[(-0.3417, 0.001167, 9.5e-6)], (0.001088, 0.001229)],
                               [[(-0.05865, 0.001366, 9e-6), (-0.1622, 0.001458, 2.5e-6)], (0.001327, 0.001531)]]
    return params.get(name)  # returns None if params-dict has no key 'name'


def makeHFSGraph(name, xmin, xmax):
    ch2 = OPData.fromPath('../data/part2/04.16/%s.tab' % name, 2)
    ch2.filterX(xmin, xmax)

    deltaY = 0.05

    c = TCanvas('c-%s' % name, '', 1280, 720)
    g2 = ch2.makeGraph('g2-%s' % name)
    prepareGraph(g2, 2)
    g2.GetXaxis().SetRangeUser(xmin, xmax)
    g2.SetMinimum(ch2.getMinY() - deltaY)
    g2.SetMaximum(ch2.getMaxY() + deltaY)
    g2.Draw('APX')

    fitStartParams = getHFSFitStartParams(name)
    fitres = []
    if fitStartParams:
        print('got start params, starting to building fit functions')
        peakNum = 0
        offset = ch2.getY()[0]  # approx offset of underground
        slope = (ch2.getY()[-1] - ch2.getY()[0]) / (xmax - xmin)  # approx slope of underground
        isUp = name[:2] == 'up'
        for peakparams, xstartend in fitStartParams:
            xstart, xend = xstartend
            peakcount = len(peakparams)
            print('peakNum: ', peakNum)
            fitfunc = 'pol1(0)+gaus(2)'
            dpc = 2  # delta param count
            for i in range(1, peakcount):
                fitfunc += '+gaus(%d)' % (i * 3 + dpc)
            fit = Fitter('fitHFS%s_%d' % (name, peakNum), fitfunc)
            fit.function.SetLineColor(getRootColor(peakNum))
            fit.setParam(0, 'a', offset)
            fit.setParamLimits(0, 0, offset * 2)
            fit.setParam(1, 'b', slope)
            if isUp:
                fit.setParamLimits(1, 0, 2 * slope)
            else:
                fit.setParamLimits(1, 2 * slope, 0)
            for i, params in enumerate(peakparams):
                fit.setParam(i * 3 + dpc, 'A%d' % i, params[0])
                fit.setParam(i * 3 + dpc + 1, 'c%d' % i, params[1])
                fit.setParam(i * 3 + dpc + 2, 's%d' % i, params[2])
                if params[0] < 0:
                    fit.setParamLimits(i * 3 + dpc, 3 * params[0], 0)
                else:
                    fit.setParamLimits(i * 3 + dpc, 0, 2 * params[0])
                fit.setParamLimits(i * 3 + dpc + 1, params[1] - 2 * params[2], params[1] + 2 * params[2])
                fit.setParamLimits(i * 3 + dpc + 2, 0, 20 * params[2])
            fit.fit(g2, xstart, xend, 'M+')
            fit.saveData('../fit/part2/%s-%d.txt' % (name, peakNum))
            for i in range(len(peakparams)):
                fitres.append((fit.params[i * 3 + dpc + 1]['value'], 0.2 * fit.params[i * 3 + dpc + 2]['value']))
            peakNum += 1

    g2.Draw('P')
    c.Update()
    c.Print('../img/part2/%s_fit.pdf' % name, 'pdf')
    return fitres


def evalHFSPeakData():
    files = os.listdir(os.path.join(os.getcwd(), DIR))
    fitres = dict()
    for file in filter(lambda s: 'hfs_zoom' in s, files):
        print('eval ' + file)
        fitres[file.split('-')[0]] = makeHFSGraph(file[:-4], 0.0004, 0.0016)
    return fitres


def compareSpectrum(prefix, spectrum):
    litvals = (-3.07, -2.25, mean([-1.48, -1.12]), mean([1.56, 1.92]), 3.76, 4.58)
    reflit = litvals[3]
    litvals = list(map(lambda x: x - reflit, litvals))
    xlist = list(zip(*spectrum))[0]
    sxlist = list(zip(*spectrum))[1]

    compData = DataErrors.fromLists(xlist, litvals, sxlist, [0] * len(litvals))

    c = TCanvas('c_%s_compspectrum' % prefix, '', 1280, 720)
    g = compData.makeGraph('g_%s_compspectrum' % prefix, 'experimentell bestimmte HFS-Aufspaltung #Delta #nu_{exp} / GHz', 'theoretische HFS-Aufspaltung #Delta #nu_{theo} / GHz')
    g.Draw('AP')

    fit = Fitter('fit_%s_compspectum' % prefix, 'pol1(0)')
    fit.setParam(0, 'a', 0)
    fit.setParam(1, 'b', 1)
    fit.fit(g, compData.getMinX() - 0.5, compData.getMaxX() + 0.5)

    l = TLegend(0.15, 0.6, 0.425, 0.85)
    l.SetTextSize(0.03)
    l.AddEntry(g, 'Spektrum', 'p')
    l.AddEntry(fit.function, 'Fit mit a + b x', 'l')
    fit.addParamsToLegend(l, [('%.2f', '%.2f'), ('%.3f', '%.3f')], chisquareformat='%.2f', units=['GHz', ''])
    l.Draw()

    c.Update()
    c.Print('../img/part2/%s-spectrum.pdf' % prefix, 'pdf')


def main():
    print('make graphs')
    print('===========')
    makeGraphs()
    print('eval etalon data')
    print('================')
    freqCalibrations = evalEtalonData()
    print('eval hfs peak data')
    print('==================')
    hfspeaks = evalHFSPeakData()
    for key in freqCalibrations.keys():
        gps, sgps = freqCalibrations[key]
        isUp = key[:2] == "up"
        spectrum = []
        if isUp:
            refpeak, srefpeak = hfspeaks[key][2]
            m = 1
        else:
            refpeak, srefpeak = hfspeaks[key][3]
            m = -1
        for peak, speak in hfspeaks[key]:
            freq = m * (refpeak - peak) * 1000 * gps
            if not compare2Floats(refpeak, peak):
                sfreq = abs(freq) * sqrt((sgps / gps) ** 2 + (sqrt(srefpeak ** 2 + speak ** 2) / (refpeak - peak)) ** 2)
            else:
                sfreq = 1000 * gps * speak
            spectrum.append((freq, sfreq))
        if isUp:
            spectrum.reverse()
        compareSpectrum('up' if isUp else 'down', spectrum)


if __name__ == '__main__':
    setupROOT()
    main()
